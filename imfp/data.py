"""Legacy ``imf_*`` interface, retained for backward compatibility.

Every function in this module is deprecated in favor of the econdataverse-style
API in :mod:`imfp.api`. See ``_DEPRECATION_MAP`` for the replacement of each.

The request-building and response-parsing mechanics these functions rely on
live in :mod:`imfp.utils`, shared with the new API so both paths return
identical data. ``_parse_imf_sdmx_json`` and ``_transform_period_for_frequency``
are re-exported here because they were previously defined in this module.
"""

import logging
from typing import Any, Literal, TypeVar, overload
from urllib.parse import urlencode
from warnings import warn

from pandas import DataFrame

from .api import imf_get_dataflows
from .utils import (
    IMF_API_BASE_URL,
    _build_data_request,
    _component_codelist,
    _download_parse,
    _dsd_component_rows,
    _extract_first,
    _find_dataflow,
    _imf_dimensions,
    _require_bool,
    _require_int,
    _require_str,
)

# _parse_imf_sdmx_json and _transform_period_for_frequency moved to utils so the
# new API can share them. They are re-exported here, in the explicit
# "import X as X" form, because they used to be defined in this module and the
# pre-2.0 tests still import them from it.
from .utils import _parse_imf_sdmx_json as _parse_imf_sdmx_json
from .utils import _transform_period_for_frequency as _transform_period_for_frequency

logger = logging.getLogger(__name__)

_FREQ_ALIASES = ("freq", "frequency")
_REF_AREA_ALIASES = ("ref_area", "refarea", "ref-area", "country", "geo")

# Dimension filter kwargs accept one code or a list of codes.
DimensionFilter = str | list[str]
_T = TypeVar("_T")

# Legacy function -> the econdataverse-style function that replaces it.
_DEPRECATION_MAP = {
    "imf_databases": "imf_get_dataflows",
    "imf_parameters": "imf_get_codelists",
    "imf_parameter_defs": "imf_get_datastructure",
    "imf_dataset": "imf_get",
}


def _warn_deprecated(name: str) -> None:
    """Emit the standard deprecation notice for a legacy ``imf_*`` function."""
    warn(
        f"imfp.{name}() is deprecated and will be removed in imfp 3.0.0. "
        f"Use imfp.{_DEPRECATION_MAP[name]}() instead. See "
        "https://promptlytechnologies.com/imfp/ for the migration guide.",
        DeprecationWarning,
        stacklevel=3,
    )


def _normalize_year_arg(value: Any, arg_name: str) -> str | None:
    """Validate and normalize a four-digit year argument to a string."""
    if value is None:
        return None
    if arg_name == "start_year":
        message = "start_year must be a four-digit number, either integer or string."
    else:
        message = "end_year must be a four-digit number, either integer or string"
    try:
        year = str(value)
        if year.isdigit() and len(year) == 4:
            return year
        raise ValueError(message)
    except Exception:
        raise ValueError(message)


def _map_parameter_alias(key: str, available_keys: set[str]) -> str:
    """Map a legacy/alias parameter name onto a dataset-specific key."""
    kl = key.lower()
    if kl in available_keys:
        return kl
    for aliases in (_FREQ_ALIASES, _REF_AREA_ALIASES):
        if kl in aliases:
            for cand in aliases:
                if cand in available_keys:
                    if cand != kl:
                        warn(f"Coercing parameter '{key}' to '{cand}' for this dataset")
                    return cand
    return kl


def _coerce_input_keys_for_dataset(
    input_dict: dict[str, _T], available_keys: set[str]
) -> dict[str, _T]:
    """Coerce legacy input parameter names to dataset-specific keys."""
    coerced: dict[str, _T] = {}
    for k, v in input_dict.items():
        new_k = _map_parameter_alias(k, available_keys)
        if new_k in coerced and new_k != k:
            warn(f"Duplicate values for '{new_k}' after coercion; keeping the first")
            continue
        coerced[new_k] = v
    return coerced


def _codes_from_parameters(parameters: dict[str, DataFrame]) -> dict[str, list[str]]:
    return {
        key: [str(code) for code in frame["input_code"]]
        for key, frame in parameters.items()
    }


def _validate_dimension_filters(kwargs: dict[str, Any]) -> dict[str, DimensionFilter]:
    """Narrow and validate **kwargs dimension filters to str | list[str]."""
    validated: dict[str, DimensionFilter] = {}
    for key, value in kwargs.items():
        if isinstance(value, str):
            validated[key] = value
            continue
        if isinstance(value, list):
            bad = [type(item).__name__ for item in value if not isinstance(item, str)]
            if bad:
                raise TypeError(
                    f"Dimension filter '{key}' must be a str or list[str]; "
                    f"got list containing {', '.join(sorted(set(bad)))}"
                )
            validated[key] = value
            continue
        raise TypeError(
            f"Dimension filter '{key}' must be a str or list[str]; "
            f"got {type(value).__name__}"
        )
    return validated


def _codes_from_kwargs(kwargs: dict[str, DimensionFilter]) -> dict[str, list[str]]:
    selected: dict[str, list[str]] = {}
    for key, value in kwargs.items():
        selected[key] = value if isinstance(value, list) else [value]
    return selected


def _apply_selected_codes(
    data_dimensions: dict[str, DataFrame],
    selected: dict[str, list[str]],
    database_id: str,
) -> None:
    """Filter data_dimensions in place to the selected input codes."""
    for key, codes in selected.items():
        if key not in data_dimensions:
            raise ValueError(
                f"{key} not valid parameter(s) for the "
                f"{database_id} database. Use "
                f"imf_parameters('{database_id}') to get "
                "valid parameters."
            )
        valid_codes = data_dimensions[key]["input_code"].tolist()
        invalid = [x for x in codes if x not in valid_codes]
        if invalid:
            warn(
                f"{invalid} not valid value(s) for {key} and will "
                f"be ignored. Use imf_parameters('{database_id}') to get "
                "valid parameters."
            )
        # Empty or all-codes selection means "no filter" (wildcard in the key).
        if set(codes) == set(valid_codes) or len(codes) == 0:
            data_dimensions[key] = data_dimensions[key].iloc[0:0]
        else:
            data_dimensions[key] = data_dimensions[key][
                data_dimensions[key]["input_code"].isin(codes)
            ]

    for key in data_dimensions:
        if key not in selected:
            data_dimensions[key] = data_dimensions[key].iloc[0:0]


def _codes_in_parameter_order(
    selected: list[str] | set[str], codebook: DataFrame
) -> list[str]:
    """Return selected input codes in ``imf_parameters`` / codelist order.

    The IMF series key joins multiple codes for a dimension with '+'. The API
    expects those codes in the same order they appear in the parameter
    codebook (for frequency, that matches alphabetized-by-description order
    for A/M/Q), not the caller's list order.
    """
    if codebook.empty or not selected:
        return []
    selected_set = set(selected)
    return [code for code in codebook["input_code"].tolist() if code in selected_set]


def _normalized_dimension_filters(
    data_dimensions: dict[str, DataFrame],
    parameter_codebooks: dict[str, DataFrame],
) -> dict[str, list[str]]:
    """Build uppercased dimension filters with codes in codebook order."""
    norm_dims: dict[str, list[str]] = {}
    for key, frame in data_dimensions.items():
        selected = frame["input_code"].tolist()
        codes = _codes_in_parameter_order(selected, parameter_codebooks[key])
        if codes:
            norm_dims[key.upper()] = codes
    return norm_dims


def imf_databases(times: int = 3) -> DataFrame:
    """
    List IMF database IDs and descriptions

    .. deprecated:: 2.0.0
       Use :func:`imfp.imf_get_dataflows` instead. This function will be
       removed in imfp 3.0.0.

    Returns a DataFrame with database_id and text description for each
    database available through the IMF API endpoint.

    Parameters
    ----------
    times : int, optional, default 3
        Maximum number of API requests to attempt.

    Returns
    -------
    pandas.DataFrame
        DataFrame containing database_id and description columns.

    Examples
    --------
    # Return first 6 IMF database IDs and descriptions
    databases = imf_databases()
    """
    _require_int(times, "times", minimum=1)

    _warn_deprecated("imf_databases")

    dataflows = imf_get_dataflows(max_tries=times)

    # The legacy contract calls the dataflow's name its "description", and
    # promises no missing values, so fall back through name -> description -> "".
    description = dataflows["name"].fillna(dataflows["description"]).fillna("")

    return DataFrame(
        {
            "database_id": dataflows["id"],
            "description": description,
        }
    ).reset_index(drop=True)


def imf_parameters(database_id: str, times: int = 2) -> dict[str, DataFrame]:
    """
    List input parameters and available parameter values for use in
    making API requests from a given IMF database.

    .. deprecated:: 2.0.0
       Use :func:`imfp.imf_get_codelists` instead, which returns a single tidy
       DataFrame rather than a dict of DataFrames. This function will be
       removed in imfp 3.0.0.

    Parameters
    ----------
    database_id : str
        A database_id from imf_databases().
    times : int, optional, default 3
        Maximum number of API requests to attempt.

    Returns
    -------
    dict
        A dictionary of DataFrames, where each key corresponds to an input
        parameter for API requests from the database. All values are DataFrames
        with an 'input_code' column and a 'description' column. The
        'input_code' column is a character list of all possible input codes for
        that parameter when making requests from the IMF API endpoint. The
        'descriptions' column is a character list of text descriptions of what
        each input code represents.

    Examples
    --------
    # Fetch the full list of indicator codes and descriptions for the Primary
    # Commodity Price System database
    params = imf_parameters(database_id='PCPS')
    """
    _require_str(database_id, "database_id")
    _require_int(times, "times", minimum=1)

    _warn_deprecated("imf_parameters")

    try:
        rows = _dsd_component_rows(database_id, times=times)
    except ValueError as e:
        raise ValueError(
            f"{e}\n\nDid you supply a valid database_id? Use imf_databases to find."
        )

    memo: dict[str, Any] = {}
    parameter_list = {}
    for row in rows:
        ref, codes = _component_codelist(row["component"], times=times, memo=memo)
        # inputs_only semantics: unenumerated dimensions are not filterable.
        if not codes:
            continue

        input_codes = []
        descriptions = []
        for code in codes:
            code_id = _extract_first(code.get("id"))
            if not code_id:
                continue
            name = _extract_first(code.get("name"))
            description = _extract_first(code.get("description"))
            input_codes.append(code_id)
            descriptions.append(name or description or code_id)

        parameter_list[row["dimension_id"].lower()] = DataFrame(
            {"input_code": input_codes, "description": descriptions}
        )

    if not parameter_list:
        raise ValueError(
            f"No filterable parameters found for {database_id}. "
            "Did you supply a valid database_id? Use imf_databases to find."
        )

    return parameter_list


def imf_parameter_defs(
    database_id: str, times: int = 3, inputs_only: bool = True
) -> DataFrame:
    """
    Get text descriptions of input parameters used in making API
    requests from a given IMF database

    .. deprecated:: 2.0.0
       Use :func:`imfp.imf_get_datastructure` instead. This function will be
       removed in imfp 3.0.0.

    Parameters
    ----------
    database_id : str
        A database_id from imf_databases().
    times : int, optional, default 3
        Maximum number of API requests to attempt.
    inputs_only : bool, optional, default False
        Whether to return only parameters used as inputs in API requests,
        or also output variables.

    Returns
    -------
    pandas.DataFrame
        A DataFrame of input parameters used in making API requests
        from a given IMF database, along with text descriptions or definitions
        of those parameters. Useful in cases when parameter names returned by
        imf_databases() are not self-explanatory. (Note that the usefulness
        of text descriptions can be uneven, depending on the database design.)

    Examples
    --------
    # Get names and text descriptions of parameters used in IMF API calls to
    # the Primary Commodity Price System database
    param_defs = imf_parameter_defs(database_id='PCPS')
    """
    _require_str(database_id, "database_id")
    _require_int(times, "times", minimum=1)
    _require_bool(inputs_only, "inputs_only")

    _warn_deprecated("imf_parameter_defs")

    try:
        parameterlist = _imf_dimensions(database_id, times, inputs_only)[
            ["parameter", "description"]
        ]
    except ValueError as e:
        if "There is an issue" in str(e):
            raise ValueError(
                f"{e}\n\nDid you supply a valid database_id? Use imf_databases to find."
            )
        else:
            raise ValueError(e)

    return parameterlist


@overload
def imf_dataset(
    database_id: str,
    parameters: dict[str, DataFrame] | None = None,
    start_year: int | str | None = None,
    end_year: int | str | None = None,
    return_raw: Literal[False] = False,
    print_url: bool = False,
    times: int = 3,
    include_metadata: Literal[False] = False,
    **kwargs: DimensionFilter,
) -> DataFrame: ...


@overload
def imf_dataset(
    database_id: str,
    parameters: dict[str, DataFrame] | None = None,
    start_year: int | str | None = None,
    end_year: int | str | None = None,
    return_raw: Literal[False] = False,
    print_url: bool = False,
    times: int = 3,
    include_metadata: Literal[True] = True,
    **kwargs: DimensionFilter,
) -> tuple[dict[str, Any], DataFrame]: ...


@overload
def imf_dataset(
    database_id: str,
    parameters: dict[str, DataFrame] | None = None,
    start_year: int | str | None = None,
    end_year: int | str | None = None,
    return_raw: Literal[True] = True,
    print_url: bool = False,
    times: int = 3,
    include_metadata: Literal[False] = False,
    **kwargs: DimensionFilter,
) -> dict[str, Any]: ...


@overload
def imf_dataset(
    database_id: str,
    parameters: dict[str, DataFrame] | None = None,
    start_year: int | str | None = None,
    end_year: int | str | None = None,
    return_raw: Literal[True] = True,
    print_url: bool = False,
    times: int = 3,
    include_metadata: Literal[True] = True,
    **kwargs: DimensionFilter,
) -> tuple[dict[str, Any], dict[str, Any]]: ...


def imf_dataset(
    database_id: str,
    parameters: dict[str, DataFrame] | None = None,
    start_year: int | str | None = None,
    end_year: int | str | None = None,
    return_raw: bool = False,
    print_url: bool = False,
    times: int = 3,
    include_metadata: bool = False,
    **kwargs: DimensionFilter,
) -> DataFrame | dict[str, Any] | tuple[dict[str, Any], DataFrame | dict[str, Any]]:
    """
    Download a data series from the IMF.

    .. deprecated:: 2.0.0
       Use :func:`imfp.imf_get` instead. This function will be removed in
       imfp 3.0.0.

    Args:
        database_id (str): Database ID for the database from which you would
                           like to request data. Can be found using
                           imf_databases().
        parameters (dict): Dictionary of data frames providing input parameters
                           for your API request. Retrieve dictionary of all
                           possible input parameters using imf_parameters() and
                           filter each data frame in the dictionary to reduce
                           it to the inputs you want.
        start_year (int, optional): Four-digit year. Earliest year for which
                                    you would like to request data.
        end_year (int, optional): Four-digit year. Latest year for which you
                                  would like to request data.
        return_raw (bool, optional): Whether to return the raw list returned by
                                     the API instead of a cleaned-up data
                                     frame.
        print_url (bool, optional): Whether to print the URL used in the API
                                    call.
        times (int, optional): Maximum number of requests to attempt.
        include_metadata (bool, optional): Whether to return the database
                                           metadata header along with the data
                                           series.
        **kwargs: Dimension filters as keyword arguments. Each value must be a
                  code string or a list of code strings. Use imf_parameters() to
                  identify which parameters to use for requests from a given
                  database and to see all valid input codes for each parameter.

    Returns:
        If return_raw == False and include_metadata == False, returns a pandas
        DataFrame with the data series. If return_raw == False but
        include_metadata == True, returns a tuple whose first item is the
        database header, and whose second item is the pandas DataFrame. If
        return_raw == True, returns the raw JSON fetched from the API endpoint.
    """
    _require_str(database_id, "database_id")
    _require_int(times, "times", minimum=1)
    _require_bool(return_raw, "return_raw")
    _require_bool(print_url, "print_url")
    _require_bool(include_metadata, "include_metadata")
    if parameters is not None and not isinstance(parameters, dict):
        raise TypeError(
            "parameters must be a dict of DataFrames from imf_parameters(); "
            f"got {type(parameters).__name__}."
        )

    _warn_deprecated("imf_dataset")

    start_period = _normalize_year_arg(start_year, "start_year")
    end_period = _normalize_year_arg(end_year, "end_year")
    dimension_filters = _validate_dimension_filters(kwargs)

    # Keep an unfiltered copy so multi-value key segments can be ordered by
    # codebook position even if filtered frames are later rearranged.
    data_dimensions = imf_parameters(database_id, times)
    parameter_codebooks = {key: frame.copy() for key, frame in data_dimensions.items()}
    available_keys = set(data_dimensions.keys())

    if parameters is not None:
        parameters = _coerce_input_keys_for_dataset(parameters, available_keys)
        if dimension_filters:
            warn(
                "Parameters list argument cannot be combined with character "
                "vector parameters arguments. Character vector parameters "
                "arguments will be ignored."
            )
        _apply_selected_codes(
            data_dimensions, _codes_from_parameters(parameters), database_id
        )
    elif dimension_filters:
        dimension_filters = _coerce_input_keys_for_dataset(
            dimension_filters, available_keys
        )
        _apply_selected_codes(
            data_dimensions, _codes_from_kwargs(dimension_filters), database_id
        )
    else:
        print(
            "User supplied no filter parameters for the API request. "
            "imf_dataset will attempt to request the entire database."
        )
        for key in data_dimensions:
            data_dimensions[key] = data_dimensions[key].iloc[0:0]

    norm_dims = _normalized_dimension_filters(data_dimensions, parameter_codebooks)

    # One dataflow lookup serves both DSD resolution and provider agency.
    flow_row = _find_dataflow(database_id, times=times)
    data_path, query_params = _build_data_request(
        database_id,
        norm_dims,
        start_period=start_period,
        end_period=end_period,
        times=times,
        flow_row=flow_row,
    )

    if print_url:
        full_url = f"{IMF_API_BASE_URL.rstrip('/')}/{data_path}"
        if query_params:
            full_url += "?" + urlencode(query_params)
        print(full_url)

    message = _download_parse(data_path, times=times, query_params=query_params)

    if return_raw:
        if include_metadata:
            metadata: dict[str, Any] = {}
            return metadata, message
        return message

    result = _parse_imf_sdmx_json(message)
    if result.empty:
        raise ValueError(
            "No data found for that combination of parameters. "
            "Try making your request less restrictive."
        )

    result.columns = result.columns.str.lower()
    if include_metadata:
        metadata = {}
        return metadata, result
    return result
