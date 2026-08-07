"""Econdataverse-style client for the IMF SDMX 3.0 Data API.

This module follows the conventions shared across the
`econdataverse <https://econdataverse.org/>`_ family of packages, and mirrors
the R package `imfapi <https://github.com/Teal-Insights/r-imfapi>`_ so that the
same workflow reads the same way in either language:

1. :func:`imf_get_dataflows` — discover the available datasets.
2. :func:`imf_get_datastructure` — see which dimensions a dataset can be
   filtered on.
3. :func:`imf_get_codelists` — find the valid codes for those dimensions.
4. :func:`imf_get` — fetch observations, filtered by the codes you chose.

Every function returns a tidy ``pandas.DataFrame``: one observation per row,
one variable per column.
"""

import logging
from typing import Any, Literal, overload
from warnings import warn

from pandas import DataFrame

from .utils import (
    IMF_API_BASE_URL,
    _annotation_value,
    _build_data_request,
    _component_codelist,
    _download_parse,
    _dsd_component_rows,
    _extract_first,
    _get_dataflow_rows,
    _parse_imf_sdmx_json,
    _require_bool,
    _require_int,
    _require_str,
)

logger = logging.getLogger(__name__)

# Dimension filter kwargs accept one code or a list of codes.
DimensionFilter = str | list[str]


def _normalize_dimensions(
    dimensions: dict[str, Any] | None, kwargs: dict[str, Any]
) -> dict[str, list[str]]:
    """
    (Internal) Merge and normalize dimension filters into ``{DIM: [codes]}``.

    Dimension IDs are upper-cased so that callers can write them in whatever
    case is convenient, and scalar codes are wrapped into single-item lists.

    Args:
        dimensions (dict, optional): Explicit dimension filters.
        kwargs (dict): Dimension filters passed as keyword arguments.

    Returns:
        dict: Upper-cased dimension IDs mapped to lists of string codes.

    Raises:
        TypeError: If `dimensions` is not a dict, or a code is not a string.
        ValueError: If the same dimension is supplied twice.
    """
    if dimensions is not None and not isinstance(dimensions, dict):
        raise TypeError(
            "dimensions must be a dict mapping dimension IDs to codes; "
            f"got {type(dimensions).__name__} ({dimensions!r})."
        )

    merged: dict[str, list[str]] = {}

    for source in (dimensions or {}, kwargs or {}):
        for name, codes in source.items():
            key = str(name).upper()
            if key in merged:
                raise ValueError(
                    f"Dimension '{key}' was supplied more than once. Pass each "
                    "dimension either in `dimensions` or as a keyword argument, "
                    "not both."
                )
            if codes is None:
                continue
            if isinstance(codes, str):
                codes = [codes]
            elif isinstance(codes, DataFrame):
                raise TypeError(
                    f"Dimension '{key}' was given a DataFrame. The econdataverse "
                    "API takes plain code strings; use "
                    "imf_get_codelists(...)['code'].tolist() to get them."
                )
            else:
                try:
                    codes = list(codes)
                except TypeError:
                    codes = [codes]

            bad = [c for c in codes if not isinstance(c, str)]
            if bad:
                raise TypeError(
                    f"Dimension '{key}' must be given string code(s); got {bad!r}."
                )
            normalized: list[str] = [str(code) for code in codes]
            if normalized:
                merged[key] = normalized

    return merged


def _normalize_period(period: Any, argument_name: str) -> str | None:
    """
    (Internal) Coerce a period argument to a string and reject bad shapes.

    Args:
        period: A year, or an SDMX-style period. ``None`` passes through.
        argument_name (str): Name used in the error message.

    Returns:
        str: The period as a string, or None.

    Raises:
        TypeError: If the period is not a scalar year or period string.
        ValueError: If the period is an empty string.
    """
    if period is None:
        return None
    if isinstance(period, bool) or not isinstance(period, (int, str)):
        raise TypeError(
            f"{argument_name} must be a year or period string "
            f'(e.g. 2015, "2015", "2015-Q1", "2015-01"); got '
            f"{type(period).__name__} ({period!r})."
        )
    period = str(period).strip()
    if not period:
        raise ValueError(f"{argument_name} must not be empty.")
    return period


def imf_get_dataflows(max_tries: int = 3) -> DataFrame:
    """
    List every dataset published through the IMF Data API.

    This is step 1 of the workflow: use it to find the ``dataflow_id`` of the
    dataset you want, then pass that ID to the other functions.

    Args:
        max_tries (int, optional): Maximum number of requests to attempt.
            Defaults to 3.

    Returns:
        pandas.DataFrame: One row per dataflow, with columns ``id``, ``name``,
        ``description``, ``version``, ``agency``, ``structure``, and
        ``last_updated``.

    Raises:
        TypeError: If max_tries is not an integer.
        ValueError: If max_tries is less than 1, or the API returns no dataflows.

    Examples:
        # Find the ID of the Primary Commodity Price System dataset
        dataflows = imf_get_dataflows()
        dataflows[dataflows["id"] == "PCPS"]
    """
    _require_int(max_tries, "max_tries", minimum=1)

    rows = []
    for flow in _get_dataflow_rows(times=max_tries):
        flow_id = _extract_first(flow.get("id"))
        if flow_id is None:
            continue
        rows.append(
            {
                "id": flow_id,
                "name": _extract_first(flow.get("name")),
                "description": _extract_first(flow.get("description")),
                "version": _extract_first(flow.get("version")),
                "agency": _extract_first(flow.get("agencyID")),
                "structure": _extract_first(flow.get("structure")),
                "last_updated": _annotation_value(flow, "lastUpdatedAt"),
            }
        )

    return DataFrame(
        rows,
        columns=[
            "id",
            "name",
            "description",
            "version",
            "agency",
            "structure",
            "last_updated",
        ],
    )


def imf_get_datastructure(
    dataflow_id: str,
    max_tries: int = 3,
    include_time: bool = False,
    include_measures: bool = False,
) -> DataFrame:
    """
    List the dimensions a dataset can be filtered on.

    This is step 2 of the workflow. The returned ``position`` is the dimension's
    slot in the dataset's series key, which is why the order matters: a request
    that filters on some dimensions and wildcards others still has to line them
    up positionally. :func:`imf_get` handles that for you.

    Args:
        dataflow_id (str): A dataflow ID from imf_get_dataflows().
        max_tries (int, optional): Maximum number of requests to attempt.
            Defaults to 3.
        include_time (bool, optional): Whether to also list the time dimension.
            Time is filtered through start_period/end_period rather than through
            the series key, so it is excluded by default.
        include_measures (bool, optional): Whether to also list measures (the
            observation values). Measures are outputs, not filters, so they are
            excluded by default.

    Returns:
        pandas.DataFrame: One row per component, with columns ``dimension_id``,
        ``type``, and ``position``.

    Raises:
        TypeError: If an argument has the wrong type.
        ValueError: If max_tries is less than 1, or the dataflow does not exist
            or defines no dimensions.

    Examples:
        # See what the Primary Commodity Price System can be filtered on
        imf_get_datastructure("PCPS")
    """
    _require_str(dataflow_id, "dataflow_id")
    _require_int(max_tries, "max_tries", minimum=1)
    _require_bool(include_time, "include_time")
    _require_bool(include_measures, "include_measures")

    rows = _dsd_component_rows(
        dataflow_id,
        times=max_tries,
        include_time=include_time,
        include_measures=include_measures,
    )

    result = DataFrame(
        [
            {
                "dimension_id": row["dimension_id"],
                "type": row["type"],
                "position": row["position"],
            }
            for row in rows
        ],
        columns=["dimension_id", "type", "position"],
    )
    # Nullable integer: measures have no position in the series key.
    result["position"] = result["position"].astype("Int64")
    return result


def imf_get_codelists(
    dimension_ids: str | list[str],
    dataflow_id: str,
    max_tries: int = 3,
) -> DataFrame:
    """
    Look up the valid codes for one or more of a dataset's dimensions.

    This is step 3 of the workflow: the ``code`` column holds the values to pass
    to :func:`imf_get`.

    Args:
        dimension_ids (str or list): One or more dimension IDs from
            imf_get_datastructure(). Matching is case-insensitive.
        dataflow_id (str): A dataflow ID from imf_get_dataflows().
        max_tries (int, optional): Maximum number of requests to attempt.
            Defaults to 3.

    Returns:
        pandas.DataFrame: One row per code, with columns ``dimension_id``,
        ``code``, ``name``, ``description``, ``codelist_id``,
        ``codelist_agency``, and ``codelist_version``. Dimensions that are not
        enumerated (they accept free-form values) contribute no rows.

    Raises:
        TypeError: If an argument has the wrong type.
        ValueError: If no dimension is named, if max_tries is less than 1, or if
            the dataflow does not exist or lacks a requested dimension.

    Examples:
        # Find the commodity indicator codes for PCPS
        imf_get_codelists("COMMODITY", "PCPS")

        # Fetch two dimensions at once
        imf_get_codelists(["COMMODITY", "FREQ"], "PCPS")
    """
    _require_str(dataflow_id, "dataflow_id")
    _require_int(max_tries, "max_tries", minimum=1)

    if isinstance(dimension_ids, str):
        dimension_ids = [dimension_ids]
    elif not isinstance(dimension_ids, (list, tuple)):
        raise TypeError(
            "dimension_ids must be a dimension ID or a list of them; "
            f"got {type(dimension_ids).__name__} ({dimension_ids!r})."
        )

    bad = [d for d in dimension_ids if not isinstance(d, str)]
    if bad:
        raise TypeError(f"dimension_ids must all be strings; got {bad!r}.")

    if not dimension_ids:
        raise ValueError("dimension_ids must name at least one dimension.")

    requested = [d.upper() for d in dimension_ids]

    rows = _dsd_component_rows(
        dataflow_id,
        times=max_tries,
        include_time=True,
        include_measures=True,
    )
    by_id = {row["dimension_id"].upper(): row for row in rows}

    unknown = [d for d in requested if d not in by_id]
    if unknown:
        raise ValueError(
            f"Unknown dimension(s) for {dataflow_id}: {', '.join(unknown)}. "
            f"Available: {', '.join(sorted(by_id))}. "
            f"Use imf_get_datastructure('{dataflow_id}') to list them."
        )

    memo: dict[str, Any] = {}
    records = []
    for dimension_id in requested:
        row = by_id[dimension_id]
        ref, codes = _component_codelist(row["component"], times=max_tries, memo=memo)
        if not codes:
            logger.debug(
                "Dimension %s of %s is not enumerated; no codes to list.",
                dimension_id,
                dataflow_id,
            )
            continue

        for code in codes:
            code_id = _extract_first(code.get("id"))
            if not code_id:
                continue
            records.append(
                {
                    "dimension_id": row["dimension_id"],
                    "code": code_id,
                    "name": _extract_first(code.get("name")),
                    "description": _extract_first(code.get("description")),
                    "codelist_id": ref["id"],
                    "codelist_agency": ref["agency"],
                    "codelist_version": ref["version"],
                }
            )

    return DataFrame(
        records,
        columns=[
            "dimension_id",
            "code",
            "name",
            "description",
            "codelist_id",
            "codelist_agency",
            "codelist_version",
        ],
    )


@overload
def imf_get(
    dataflow_id: str,
    dimensions: dict[str, Any] | None = None,
    start_period: int | str | None = None,
    end_period: int | str | None = None,
    max_tries: int = 3,
    print_url: bool = False,
    return_raw: Literal[False] = False,
    **kwargs: Any,
) -> DataFrame: ...


@overload
def imf_get(
    dataflow_id: str,
    dimensions: dict[str, Any] | None = None,
    start_period: int | str | None = None,
    end_period: int | str | None = None,
    max_tries: int = 3,
    print_url: bool = False,
    return_raw: Literal[True] = True,
    **kwargs: Any,
) -> dict[str, Any]: ...


def imf_get(
    dataflow_id: str,
    dimensions: dict[str, Any] | None = None,
    start_period: int | str | None = None,
    end_period: int | str | None = None,
    max_tries: int = 3,
    print_url: bool = False,
    return_raw: bool = False,
    **kwargs: Any,
) -> DataFrame | dict[str, Any]:
    """
    Fetch observations from an IMF dataset.

    This is step 4 of the workflow. Dimensions you do not filter on are
    wildcarded, so omitting ``dimensions`` entirely requests the whole dataset —
    which for most datasets is slow and very large.

    Codes are not validated before the request is sent; the API is the authority
    on what is valid. Use :func:`imf_get_codelists` to find valid codes.

    Args:
        dataflow_id (str): A dataflow ID from imf_get_dataflows().
        dimensions (dict, optional): Maps dimension IDs to the code or list of
            codes to include. Dimension IDs are matched case-insensitively.
        start_period (int or str, optional): Earliest period to return, as a
            year ("2015"), quarter ("2015-Q1"), or month ("2015-01").
        end_period (int or str, optional): Latest period to return, in the same
            formats as start_period.
        max_tries (int, optional): Maximum number of requests to attempt.
            Defaults to 3.
        print_url (bool, optional): Whether to print the request URL, which is
            useful when reporting a problem with a specific query.
        return_raw (bool, optional): Whether to return the parsed JSON response
            as a dict instead of a DataFrame.
        **kwargs: Dimension filters given as keyword arguments, e.g.
            ``freq="A"``. Equivalent to passing them in ``dimensions``.

    Returns:
        pandas.DataFrame: One row per observation, with a column per series
        dimension (named as in the datastructure), plus ``TIME_PERIOD`` and
        ``OBS_VALUE``. Returns an empty DataFrame, and warns, when the query
        matches no observations. If return_raw is True, returns the raw parsed
        JSON dict instead.

    Raises:
        TypeError: If an argument has the wrong type, including a dimension
            given something other than a code string or list of them.
        ValueError: If max_tries is less than 1, if the same dimension is
            supplied twice, or if the dataflow does not exist or lacks a named
            dimension.

    Examples:
        # Annual coal prices, 2000-2015
        imf_get(
            "PCPS",
            dimensions={"COMMODITY": "PCOAL", "FREQ": "A"},
            start_period=2000,
            end_period=2015,
        )

        # The same query using keyword arguments
        imf_get("PCPS", commodity="PCOAL", freq="A", start_period=2000)
    """
    _require_str(dataflow_id, "dataflow_id")
    _require_int(max_tries, "max_tries", minimum=1)
    _require_bool(print_url, "print_url")
    _require_bool(return_raw, "return_raw")

    dimension_filters = _normalize_dimensions(dimensions, kwargs)
    start = _normalize_period(start_period, "start_period")
    end = _normalize_period(end_period, "end_period")

    if not dimension_filters:
        logger.info("No dimension filters supplied; requesting all of %s.", dataflow_id)

    data_path, query_params = _build_data_request(
        dataflow_id,
        dimension_filters,
        start_period=start,
        end_period=end,
        times=max_tries,
    )

    if print_url:
        from urllib.parse import urlencode

        print(f"{IMF_API_BASE_URL.rstrip('/')}/{data_path}?{urlencode(query_params)}")

    message = _download_parse(data_path, times=max_tries, query_params=query_params)

    if return_raw:
        return message

    result = _parse_imf_sdmx_json(message)

    if result.empty:
        warn(
            f"No observations matched that query against {dataflow_id}. "
            "Try relaxing the dimension filters or the time window.",
            UserWarning,
        )

    return result
