import logging
import re
from typing import Any, Literal, TypeVar, overload
from urllib.parse import urlencode
from warnings import warn

import type_enforced
from pandas import DataFrame

from .utils import (
    IMF_API_BASE_URL,
    _download_parse,
    _extract_first,
    _find_dataflow,
    _get_datastructure_components,
    _imf_dimensions,
)

logger = logging.getLogger(__name__)

_FREQ_ALIASES = ("freq", "frequency")
_REF_AREA_ALIASES = ("ref_area", "refarea", "ref-area", "country", "geo")
_PERIOD_FREQ_SUFFIX = re.compile(r"^\d{4}-(M|Q|A|W)\d+$")
_PERIOD_MONTH = re.compile(r"^\d{4}-\d{2}$")
_PERIOD_YEAR = re.compile(r"^\d{4}$")

# Dimension filter kwargs accept one code or a list of codes.
DimensionFilter = str | list[str]
_T = TypeVar("_T")


def _parse_imf_sdmx_json(message: dict[str, Any]) -> DataFrame:
    """
    Parse SDMX JSON message from new API into a DataFrame.

    Matches the R implementation's parse_imf_sdmx_json function.

    Args:
        message: The JSON response from the API

    Returns:
        DataFrame with one row per observation
    """
    # Defensive checks
    if not message or not message.get("data"):
        return DataFrame()

    data_sets = message.get("data", {}).get("dataSets")
    structures = message.get("data", {}).get("structures")

    if not data_sets or len(data_sets) < 1 or not structures or len(structures) < 1:
        return DataFrame()

    ds = data_sets[0]
    st = structures[0]

    # Dimensions metadata
    series_dims = st.get("dimensions", {}).get("series", [])
    obs_dims = st.get("dimensions", {}).get("observation", [])
    obs_dim = obs_dims[0] if obs_dims and len(obs_dims) >= 1 else None

    # Helper to map index -> code/id
    def index_to_code(dim_def: dict[str, Any] | None, idx: Any) -> Any:
        if not dim_def or not dim_def.get("values") or len(dim_def["values"]) < 1:
            return None
        try:
            i = int(idx)
            i = i + 1  # Convert from 0-based to 1-based
            if i < 1 or i > len(dim_def["values"]):
                return None
            v = dim_def["values"][i - 1]  # Python is 0-based
            return v.get("id") or v.get("value")
        except (ValueError, IndexError, TypeError):
            return None

    def obs_index_to_period(idx: Any) -> Any:
        if not obs_dim or not obs_dim.get("values") or len(obs_dim["values"]) < 1:
            return None
        try:
            i = int(idx)
            i = i + 1  # Convert from 0-based to 1-based
            if i < 1 or i > len(obs_dim["values"]):
                return None
            v = obs_dim["values"][i - 1]  # Python is 0-based
            return v.get("value") or v.get("id")
        except (ValueError, IndexError, TypeError):
            return None

    # No series present -> empty DataFrame
    if not ds.get("series") or len(ds["series"]) == 0:
        return DataFrame()

    # Prepare column names for series dimensions
    series_dim_ids = []
    if series_dims and len(series_dims) > 0:
        series_dim_ids = [_extract_first(dim.get("id")) for dim in series_dims]

    # Build rows
    rows = []
    series_keys = list(ds["series"].keys())

    for sk in series_keys:
        s_entry = ds["series"][sk]
        # Decode series key indices to codes
        sk_parts = sk.split(":")
        # Ensure length matches; pad if necessary
        if len(sk_parts) < len(series_dim_ids):
            sk_parts.extend([None] * (len(series_dim_ids) - len(sk_parts)))

        series_codes = []
        if len(series_dim_ids) > 0:
            for dim_def, idx in zip(series_dims, sk_parts):
                code = index_to_code(dim_def, idx) if idx is not None else None
                series_codes.append(code)

        # Process observations
        obs_keys = list(s_entry.get("observations", {}).keys())
        if len(obs_keys) == 0:
            continue

        for ok in obs_keys:
            obs = s_entry["observations"][ok]
            # Observation value is the first element; handle None gracefully
            obs_val_raw = obs[0] if len(obs) >= 1 else None
            obs_val_num = None

            if obs_val_raw is not None:
                try:
                    obs_val_num = float(obs_val_raw)
                except (ValueError, TypeError):
                    # Map common non-numeric flags to None
                    if isinstance(obs_val_raw, str) and obs_val_raw.upper() in (
                        "NA",
                        "NP",
                        "ND",
                        "N/A",
                    ):
                        obs_val_num = None

            time_period = obs_index_to_period(ok)

            # Build row
            row = {}
            for dim_id, code in zip(series_dim_ids, series_codes):
                row[dim_id] = code
            row["TIME_PERIOD"] = time_period
            row["OBS_VALUE"] = obs_val_num
            rows.append(row)

    if len(rows) == 0:
        return DataFrame()

    # Convert to DataFrame
    df = DataFrame(rows)
    return df


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


def _series_key_rows(components: dict[str, Any]) -> list[dict[str, Any]]:
    """Return non-time dimensions sorted by position for series-key construction."""
    dims = components.get("dimensionList", {}).get("dimensions", [])
    time_dims = components.get("dimensionList", {}).get("timeDimensions", [])
    all_dim_rows: list[dict[str, Any]] = []
    for dim in list(dims) + list(time_dims or []):
        if not dim:
            continue
        dim_id = _extract_first(dim.get("id"))
        position = dim.get("position")
        dim_type = _extract_first(dim.get("type"))
        if dim_id and position is not None:
            all_dim_rows.append(
                {
                    "id": dim_id.upper(),
                    "position": int(position),
                    "type": dim_type,
                }
            )
    key_rows = [row for row in all_dim_rows if row["type"] != "TimeDimension"]
    key_rows.sort(key=lambda x: x["position"])
    return key_rows


def _build_series_key(
    key_rows: list[dict[str, Any]], norm_dims: dict[str, list[str]]
) -> str:
    available_dims = {row["id"] for row in key_rows}
    unknown = set(norm_dims) - available_dims
    if unknown:
        raise ValueError(
            f"Unknown dimension(s): {', '.join(sorted(unknown))}. "
            f"Available dimensions: {', '.join(sorted(available_dims))}"
        )
    segments = []
    for row in key_rows:
        vals = norm_dims.get(row["id"], [])
        # Omitted dimensions (including omitted frequency) become '*' wildcards.
        segments.append("*" if not vals else "+".join(vals))
    return ".".join(segments)


def _transform_period_for_frequency(
    period: str | None,
    frequency: list[str] | None,
    bound: Literal["start", "end"] = "start",
) -> str | None:
    """Transform a user time period into the SDMX filter form for a frequency.

    When ``frequency`` is a single code, year bounds use that frequency's first
    (start) or last (end) period of the year. When frequency is omitted or
    multi-valued, start uses the earliest cross-frequency suffix (``-A1``) and
    end uses a high sentinel (``-W99``) so quarterly/monthly periods in the
    requested year are not excluded by lexicographic comparison.
    """
    if not period:
        return period
    if _PERIOD_FREQ_SUFFIX.match(period):
        return period
    if _PERIOD_MONTH.match(period):
        year, month = period.split("-")
        return f"{year}-M{month}"
    if _PERIOD_YEAR.match(period):
        start_suffixes = {"A": "-A1", "Q": "-Q1", "M": "-M01", "W": "-W01"}
        end_suffixes = {"A": "-A1", "Q": "-Q4", "M": "-M12", "W": "-W53"}
        if frequency and len(frequency) == 1:
            freq = frequency[0].upper()
            suffix_map = end_suffixes if bound == "end" else start_suffixes
            suffix = suffix_map.get(freq, "-A1" if bound == "start" else "-W99")
        else:
            suffix = "-A1" if bound == "start" else "-W99"
        return f"{period}{suffix}"
    return period


def _build_time_query_params(
    start_period: str | None,
    end_period: str | None,
    user_frequency: list[str] | None,
    provider_agency: str,
) -> dict[str, str]:
    query_params = {
        "dimensionAtObservation": "TIME_PERIOD",
        "attributes": "dsd",
        "measures": "all",
    }
    time_filters = []
    if start_period:
        time_filters.append(
            f"ge:{_transform_period_for_frequency(start_period, user_frequency, bound='start')}"
        )
    if end_period:
        time_filters.append(
            f"le:{_transform_period_for_frequency(end_period, user_frequency, bound='end')}"
        )
    if time_filters:
        if provider_agency == "IMF.STA":
            query_params["c[TIME_PERIOD]"] = "+".join(time_filters)
        else:
            warn(
                f"Agency {provider_agency} does not support time filters; "
                "time window will be ignored."
            )
    return query_params


@type_enforced.Enforcer
def imf_databases(times: int = 3) -> DataFrame:
    """
    List IMF database IDs and descriptions

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
    # Use new API endpoint: structure/dataflow/all/*/+ where '+' means latest stable version
    raw_dl = _download_parse("structure/dataflow/all/*/+", times=times)

    # New API structure: body["data"]["dataflows"] is a list of dataflow objects
    raw_dataflows = raw_dl.get("data", {}).get("dataflows")
    if raw_dataflows is None:
        raise ValueError("No dataflows found in API response.")

    # Extract database_id and description from each dataflow
    # The new API structure has: id, name, description, version, agencyID, structure, annotations
    # In the R implementation, these are lists and we take the first element [[1]]
    database_id = []
    description = []

    for dataflow in raw_dataflows:
        # Extract id (database_id)
        dataflow_id = _extract_first(dataflow.get("id"))
        if dataflow_id is None:
            continue  # Skip if no ID

        # Extract name (used as description for backward compatibility)
        # The old API used Name["#text"] which was the name, not description
        name = _extract_first(dataflow.get("name"))
        if name is None:
            # Fallback to description if name is not available
            name = _extract_first(dataflow.get("description"))
            if name is None:
                name = ""  # Empty string if neither name nor description available

        database_id.append(dataflow_id)
        description.append(name)

    database_list = DataFrame({"database_id": database_id, "description": description})
    return database_list


@type_enforced.Enforcer
def imf_parameters(database_id: str, times: int = 2) -> dict[str, DataFrame]:
    """
    List input parameters and available parameter values for use in

    making API requests from a given IMF database.

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
    try:
        codelist = _imf_dimensions(database_id, times)
    except ValueError as e:
        if "There is an issue" in str(e) or "not found" in str(e).lower():
            raise ValueError(
                f"{e}\n\nDid you supply a valid database_id? Use imf_databases to find."
            )
        else:
            raise ValueError(e)

    def fetch_parameter_data(k: int, times: int) -> DataFrame:
        codelist_id = str(codelist.loc[k, "code"])
        agency_raw = codelist.loc[k, "agency"]
        codelist_agency = None if agency_raw is None else str(agency_raw)

        # Fetch codelist using new API
        # Try agency-specific path first to get the correct version,
        # then fallback to 'all' if the agency path fails
        cl_paths = []
        if codelist_agency:
            cl_paths.append(f"structure/codelist/{codelist_agency}/{codelist_id}/+")
        cl_paths.append(f"structure/codelist/all/{codelist_id}/+")

        cl_body = None
        for cl_path in cl_paths:
            try:
                cl_body = _download_parse(cl_path, times=times)
                break
            except ValueError:
                continue

        if cl_body is None:
            raise ValueError(f"Codelist {codelist_id} not found.")

        clists = cl_body.get("data", {}).get("codelists", [])
        if not clists or len(clists) < 1:
            raise ValueError(f"Empty codelists payload for {codelist_id}.")

        codes_list = clists[0].get("codes", [])
        if not codes_list:
            raise ValueError(f"No codes found in codelist {codelist_id}.")

        # Extract codes and descriptions
        input_codes = []
        code_descriptions = []

        for code_obj in codes_list:
            code_id = _extract_first(code_obj.get("id"))
            code_name = _extract_first(code_obj.get("name"))
            code_desc = _extract_first(code_obj.get("description"))

            if code_id:
                input_codes.append(code_id)
                # Use name if available, otherwise description, otherwise code_id
                desc = code_name if code_name else (code_desc if code_desc else code_id)
                code_descriptions.append(desc)

        return DataFrame(
            {
                "input_code": input_codes,
                "description": code_descriptions,
            }
        )

    parameter_list: dict[str, DataFrame] = {
        str(codelist.loc[k, "parameter"]): fetch_parameter_data(k, times)
        for k in range(codelist.shape[0])
    }

    return parameter_list


@type_enforced.Enforcer
def imf_parameter_defs(
    database_id: str, times: int = 3, inputs_only: bool = True
) -> DataFrame:
    """
    Get text descriptions of input parameters used in making API
    requests from a given IMF database

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
    components = _get_datastructure_components(
        database_id, times=times, flow_row=flow_row
    )
    key_rows = _series_key_rows(components)
    key = _build_series_key(key_rows, norm_dims)

    available_dims = {row["id"] for row in key_rows}
    freq_dim_id = next((d for d in ("FREQUENCY", "FREQ") if d in available_dims), None)
    user_frequency = norm_dims.get(freq_dim_id) if freq_dim_id else None
    provider_agency = _extract_first(flow_row.get("agencyID")) or "all"
    query_params = _build_time_query_params(
        start_period, end_period, user_frequency, provider_agency
    )

    data_path = f"data/dataflow/{provider_agency}/{database_id}/+/{key}"
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
