import logging
from typing import overload, Literal
from warnings import warn
from urllib.parse import urlencode
from pandas import DataFrame
import type_enforced

from .utils import (
    _download_parse,
    _imf_dimensions,
    _extract_first,
    _get_datastructure_components,
    IMF_API_BASE_URL,
)

logger = logging.getLogger(__name__)


def _parse_imf_sdmx_json(message: dict) -> DataFrame:
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
    def index_to_code(dim_def, idx):
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

    def obs_index_to_period(idx):
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

    def _extract_first(value):
        """Extract first element from list, or return value if not a list."""
        if isinstance(value, list) and len(value) > 0:
            return value[0]
        return value

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
                f"{e}\n\nDid you supply a valid database_id? "
                "Use imf_databases to find."
            )
        else:
            raise ValueError(e)

    def fetch_parameter_data(k, times):
        codelist_id = codelist.loc[k, "code"]
        codelist_agency = codelist.loc[k, "agency"]

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

    parameter_list = {
        codelist.loc[k, "parameter"]: fetch_parameter_data(k, times)
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
                f"{e}\n\nDid you supply a valid database_id? "
                "Use imf_databases to find."
            )
        else:
            raise ValueError(e)

    return parameterlist


@overload
def imf_dataset(
    database_id: str,
    parameters: dict | None = None,
    start_year: int | str | None = None,
    end_year: int | str | None = None,
    return_raw: bool = False,
    print_url: bool = False,
    times: int = 3,
    include_metadata: Literal[False] = False,
    **kwargs,
) -> DataFrame:
    ...


@overload
def imf_dataset(
    database_id: str,
    parameters: dict | None = None,
    start_year: int | str | None = None,
    end_year: int | str | None = None,
    return_raw: bool = False,
    print_url: bool = False,
    times: int = 3,
    include_metadata: Literal[True] = True,
    **kwargs,
) -> tuple[dict, DataFrame]:
    ...


@type_enforced.Enforcer
def imf_dataset(
    database_id: str,
    parameters: dict | None = None,
    start_year: int | str | None = None,
    end_year: int | str | None = None,
    return_raw: bool = False,
    print_url: bool = False,
    times: int = 3,
    include_metadata: bool = False,
    **kwargs,
) -> DataFrame | tuple[dict, DataFrame]:
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
        **kwargs: Additional keyword arguments for specifying parameters as
                  separate arguments. Use imf_parameters() to identify which
                  parameters to use for requests from a given database and to
                  see all valid input codes for each parameter.

    Returns:
        If return_raw == False and include_metadata == False, returns a pandas
        DataFrame with the data series. If return_raw == False but
        include_metadata == True, returns a tuple whose first item is the
        database header, and whose second item is the pandas DataFrame. If
        return_raw == True, returns the raw JSON fetched from the API endpoint.
    """
    import re

    # Normalize start_year and end_year to strings
    start_period = None
    end_period = None

    if start_year is not None:
        try:
            start_year = str(start_year)
            if start_year.isdigit() and len(start_year) == 4:
                start_period = start_year
            else:
                raise ValueError(
                    "start_year must be a four-digit number, "
                    "either integer or string."
                )
        except Exception:
            raise ValueError(
                "start_year must be a four-digit number, either integer or string."
            )

    if end_year is not None:
        try:
            end_year = str(end_year)
            if end_year.isdigit() and len(end_year) == 4:
                end_period = end_year
            else:
                raise ValueError(
                    "end_year must be a four-digit number, either integer or string"
                )
        except Exception:
            raise ValueError(
                "end_year must be a four-digit number, either integer or string"
            )

    # Get available parameters for validation
    data_dimensions = imf_parameters(database_id, times)

    # Helper to coerce legacy input parameter names to dataset-specific keys
    def _coerce_input_keys_for_dataset(
        input_dict: dict, available_keys: set[str]
    ) -> dict:
        def map_key(k: str) -> str:
            kl = k.lower()
            if kl in available_keys:
                return kl
            # Frequency aliases
            if kl in ("freq", "frequency"):
                for cand in ("frequency", "freq"):
                    if cand in available_keys:
                        if cand != kl:
                            warn(
                                f"Coercing parameter '{k}' to '{cand}' for this dataset"
                            )
                        return cand
            # ref_area aliases
            if kl in ("ref_area", "refarea", "ref-area", "country", "geo"):
                for cand in ("ref_area", "refarea", "ref-area", "country", "geo"):
                    if cand in available_keys:
                        if cand != kl:
                            warn(
                                f"Coercing parameter '{k}' to '{cand}' for this dataset"
                            )
                        return cand
            return kl

        coerced: dict = {}
        for k, v in input_dict.items():
            new_k = map_key(k)
            if new_k in coerced and new_k != k:
                warn(
                    f"Duplicate values for '{new_k}' after coercion; keeping the first"
                )
                continue
            coerced[new_k] = v
        return coerced

    if parameters is not None:
        # Coerce legacy keys in provided parameters dict
        parameters = _coerce_input_keys_for_dataset(
            parameters, set(data_dimensions.keys())
        )
        if kwargs:
            warn(
                "Parameters list argument cannot be combined with character "
                "vector parameters arguments. Character vector parameters "
                "arguments will be ignored."
            )
        for key in parameters:
            if key not in data_dimensions:
                raise ValueError(
                    f"{key} not valid parameter(s) for the "
                    f"{database_id} database. Use "
                    f"imf_parameters('{database_id}') to get "
                    "valid parameters."
                )
            invalid_keys = []
            for x in list(parameters[key]["input_code"]):
                if x not in list(data_dimensions[key]["input_code"]):
                    invalid_keys.append(x)
            if len(invalid_keys) > 0:
                warn(
                    f"{invalid_keys} not valid value(s) for {key} and will "
                    f"be ignored. Use imf_parameters('{database_id}') to get "
                    "valid parameters."
                )
            if (
                set(parameters[key]["input_code"])
                == set(data_dimensions[key]["input_code"])
                or len(parameters[key]) == 0
            ):
                data_dimensions[key] = data_dimensions[key].iloc[0:0]
            data_dimensions[key] = data_dimensions[key].iloc[
                [
                    index
                    for index, x in enumerate(data_dimensions[key]["input_code"])
                    if x in list(parameters[key]["input_code"])
                ]
            ]
        for key in data_dimensions:
            if key not in parameters:
                data_dimensions[key] = data_dimensions[key].iloc[0:0]

    elif kwargs:
        # Coerce legacy keys in kwargs
        kwargs = _coerce_input_keys_for_dataset(kwargs, set(data_dimensions.keys()))
        for key in kwargs:
            if key not in data_dimensions:
                raise ValueError(
                    f"{key} not valid parameter(s) for the "
                    f"{database_id} database. Use "
                    f"imf_parameters('{database_id}') to get "
                    "valid parameters."
                )
            invalid_vals = []
            if not isinstance(kwargs[key], list):
                kwargs[key] = [kwargs[key]]
            for x in kwargs[key]:
                if x not in data_dimensions[key]["input_code"].tolist():
                    invalid_vals.append(x)
            if len(invalid_vals) > 0:
                warn(
                    f"{invalid_vals} not valid value(s) for {key} and will "
                    f"be ignored. Use imf_parameters('{database_id}') to get "
                    "valid parameters."
                )
            if (
                set(kwargs[key]) == set(data_dimensions[key]["input_code"].tolist())
                or len(kwargs[key]) == 0
            ):
                data_dimensions[key] = data_dimensions[key].iloc[0:0]
            data_dimensions[key] = data_dimensions[key].iloc[
                [
                    index
                    for index, x in enumerate(data_dimensions[key]["input_code"])
                    if x in kwargs[key]
                ]
            ]
        for key in data_dimensions:
            if key not in kwargs:
                data_dimensions[key] = data_dimensions[key].iloc[0:0]

    else:
        print(
            "User supplied no filter parameters for the API request. "
            "imf_dataset will attempt to request the entire database."
        )
        for key in data_dimensions:
            data_dimensions[key] = data_dimensions[key].iloc[0:0]

    # Normalize dimension filters (build dict mapping dimension names to code lists)
    norm_dims = {}
    for key in data_dimensions:
        codes = data_dimensions[key]["input_code"].tolist()
        if codes:
            norm_dims[key.upper()] = codes

    # Fetch DSD components to get dimension order
    components = _get_datastructure_components(database_id, times)
    dims = components.get("dimensionList", {}).get("dimensions", [])
    time_dims = components.get("dimensionList", {}).get("timeDimensions", [])

    # Build list of all dimensions with position
    all_dim_rows = []
    for dim in dims:
        if dim:
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

    if time_dims:
        for dim in time_dims:
            if dim:
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

    # Series key uses non-time dimensions (TIME_PERIOD varies at observation)
    key_rows = [row for row in all_dim_rows if row["type"] != "TimeDimension"]
    key_rows.sort(key=lambda x: x["position"])

    # Validate requested dimension names exist
    requested_dims = set(norm_dims.keys())
    available_dims = {row["id"] for row in key_rows}
    unknown = requested_dims - available_dims
    if unknown:
        raise ValueError(
            f"Unknown dimension(s): {', '.join(sorted(unknown))}. "
            f"Available dimensions: {', '.join(sorted(available_dims))}"
        )

    # Build dot-separated key with plus-separated codes per position
    segments = []
    for row in key_rows:
        dim_id = row["id"]
        vals = norm_dims.get(dim_id, [])
        if not vals:
            segments.append("*")
        else:
            segments.append("+".join(vals))

    key = ".".join(segments)

    # Helper to transform time periods for API compatibility
    def transform_period_for_frequency(period, frequency):
        if not period:
            return period

        # Check if already in SDMX format with frequency suffix
        if re.match(r"^\d{4}-(M|Q|A|W)\d+$", period):
            return period

        # User-friendly month format: "2019-01" to "2019-12"
        if re.match(r"^\d{4}-\d{2}$", period):
            parts = period.split("-")
            return f"{parts[0]}-M{parts[1]}"

        # Plain year (e.g., "2015") needs frequency-specific suffix
        if re.match(r"^\d{4}$", period):
            if frequency and len(frequency) == 1:
                freq_map = {"A": "-A1", "Q": "-Q1", "M": "-M01", "W": "-W01"}
                suffix = freq_map.get(frequency[0].upper(), "-A1")
            else:
                suffix = "-A1"  # default when frequency is wildcarded
            return f"{period}{suffix}"

        return period

    # Extract frequency from user's dimension filter (if provided), dynamically resolving the dimension id
    freq_dim_candidates = ["FREQUENCY", "FREQ"]
    freq_dim_id = next((d for d in freq_dim_candidates if d in available_dims), None)
    user_frequency = norm_dims.get(freq_dim_id) if freq_dim_id else None

    # Build query params
    query_params = {
        "dimensionAtObservation": "TIME_PERIOD",
        "attributes": "dsd",
        "measures": "all",
    }

    # Apply time filters
    time_filters = []
    if start_period:
        transformed_start = transform_period_for_frequency(start_period, user_frequency)
        time_filters.append(f"ge:{transformed_start}")
    if end_period:
        transformed_end = transform_period_for_frequency(end_period, user_frequency)
        time_filters.append(f"le:{transformed_end}")

    # Determine dataflow agency (owner)
    raw_dl = _download_parse("structure/dataflow/all/*/+", times=times)
    raw_dataflows = raw_dl.get("data", {}).get("dataflows", [])
    flow_row = None
    for flow in raw_dataflows:
        flow_id = _extract_first(flow.get("id"))
        if flow_id == database_id:
            flow_row = flow
            break

    if flow_row is None:
        raise ValueError(f"Dataflow not found or not unique: {database_id}.")

    provider_agency = _extract_first(flow_row.get("agencyID"))
    if not provider_agency:
        provider_agency = "all"

    # Apply time filter only for IMF.STA via c[TIME_PERIOD]
    if time_filters:
        if provider_agency == "IMF.STA":
            query_params["c[TIME_PERIOD]"] = "+".join(time_filters)
        else:
            warn(
                f"Agency {provider_agency} does not support time filters; "
                "time window will be ignored."
            )

    # Build path and perform request
    data_path = f"data/dataflow/{provider_agency}/{database_id}/+/{key}"

    if print_url:
        full_url = f"{IMF_API_BASE_URL.rstrip('/')}/{data_path}"
        if query_params:
            full_url += "?" + urlencode(query_params)
        print(full_url)

    message = _download_parse(data_path, times=times, query_params=query_params)

    if return_raw:
        if include_metadata:
            # For now, return empty metadata dict (could be enhanced later)
            metadata = {}
            return metadata, message
        else:
            return message

    # Parse SDMX JSON message into DataFrame
    result = _parse_imf_sdmx_json(message)

    if result.empty:
        raise ValueError(
            "No data found for that combination of parameters. "
            "Try making your request less restrictive."
        )

    # Convert column names to lowercase for backward compatibility
    result.columns = result.columns.str.lower()

    if not include_metadata:
        return result
    else:
        metadata = {}  # Could be enhanced to extract from message later
        return metadata, result
