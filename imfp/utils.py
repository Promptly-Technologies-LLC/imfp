from os import environ, path
import hashlib
from time import sleep, perf_counter
from requests import get
from json import loads, load, dump, JSONDecodeError
from pandas import DataFrame
from urllib.parse import urlparse, urljoin
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# New IMF API base URL
IMF_API_BASE_URL = "https://api.imf.org/external/sdmx/3.0/"


def _min_wait_time_limited(default_wait_time=1.5):
    def decorator(func):
        last_called = [0.0]

        def wrapper(*args, **kwargs):
            min_wait_time = float(environ.get("IMF_WAIT_TIME", default_wait_time))
            elapsed = perf_counter() - last_called[0]
            left_to_wait = min_wait_time - elapsed
            if left_to_wait > 0:
                sleep(left_to_wait)
            ret = func(*args, **kwargs)
            last_called[0] = perf_counter()
            return ret

        return wrapper

    return decorator


@_min_wait_time_limited()
def _imf_get(url, headers, timeout=None):
    """
    A rate-limited wrapper around the requests.get method.

    Args:
        url (str): The URL to send a GET request to.
        headers (dict): The headers to use in the API request.
        timeout (float, optional): Timeout in seconds for the request.

    Returns:
        requests.Response: The response object returned by requests.get.

    Usage:
        response = _imf_get(
                'https://api.imf.org/external/sdmx/3.0/structure/',
                headers={'Accept': 'application/json'}
            )
        print(response.text)
    """
    logger.debug(f"Sending GET request to {url}")
    response = get(url, headers=headers, timeout=timeout)
    return response


_imf_use_cache = False
_imf_save_response = False


def _download_parse(
    resource_or_url,
    times=3,
    base_url=None,
    query_params=None,
    timeout_seconds=30.0,
    low_speed_seconds=15.0,
):
    """
    (Internal) Download and parse JSON content from the IMF API with rate limiting
    and retries.

    This function is rate-limited and will perform a specified number of
    retries in case of failure. It supports both the new API (resource paths)
    and legacy full URLs for backward compatibility.

    Args:
        resource_or_url (str): Either a resource path (e.g., 'structure/') for the
            new API, or a full URL for backward compatibility.
        times (int, optional): The number of times to retry the request in case
            of failure. Defaults to 3.
        base_url (str, optional): Base URL for the API. Defaults to the new IMF API.
        query_params (dict, optional): Query parameters to append to the URL.
        timeout_seconds (float, optional): Timeout in seconds for the request.
            Defaults to 30.0.
        low_speed_seconds (float, optional): Currently not fully implemented in
            requests library, but kept for API compatibility. Defaults to 15.0.

    Returns:
        dict: The parsed JSON content as a Python dictionary.

    Raises:
        ValueError: If the content cannot be parsed as JSON after the specified
        number of retries, or if the resource path is invalid.
    """
    global _imf_use_cache, _imf_save_response
    use_cache = _imf_use_cache
    save_response = _imf_save_response

    # Validate resource_or_url
    if not resource_or_url or not isinstance(resource_or_url, str):
        raise ValueError("resource_or_url must be a non-empty string")

    # Determine if it's a full URL or a resource path
    parsed = urlparse(resource_or_url)
    is_full_url = parsed.scheme in ("http", "https")

    if is_full_url:
        # Legacy mode: full URL provided
        if base_url:
            raise ValueError(
                "base_url cannot be provided when resource_or_url is a full URL"
            )
        url = resource_or_url
        resource = resource_or_url  # For error messages
    else:
        # New API mode: resource path provided
        if base_url is None:
            base_url = IMF_API_BASE_URL

        # Validate resource path doesn't start with http:// or https://
        if re.match(r"^https?://", resource_or_url):
            raise ValueError(
                "resource_or_url should be a path (e.g., 'structure/'), not a full URL."
            )

        # Build URL from base_url and resource path
        url = urljoin(base_url.rstrip("/") + "/", resource_or_url.lstrip("/"))
        resource = resource_or_url

        # Add query parameters if provided
        if query_params:
            from urllib.parse import urlencode

            separator = "&" if "?" in url else "?"
            url += separator + urlencode(query_params)

    # Validate times parameter
    if not isinstance(times, int) or times < 1:
        raise ValueError("times must be a positive integer")

    app_name = environ.get("IMF_APP_NAME")
    if app_name:
        app_name = app_name[:255]
    else:
        app_name = (
            "imfp Python package (https://github.com/Promptly-Technologies-LLC/imfp)"
        )

    headers = {
        "Accept": "application/json",
        "User-Agent": app_name,
    }

    for attempt in range(times):
        response = None
        if use_cache:
            cached_status, cached_content = _load_cached_response(url)
            if cached_content is not None:
                content = cached_content
                status = cached_status
            else:
                response = _imf_get(url, headers=headers, timeout=timeout_seconds)
                content = response.text
                status = response.status_code
        else:
            response = _imf_get(url, headers=headers, timeout=timeout_seconds)
            content = response.text
            status = response.status_code

        if save_response:
            file_name = hashlib.sha256(url.encode()).hexdigest()
            file_path = f"tests/responses/{file_name}.json"
            print(f"Saving response to: {file_path}")
            with open(file_path, "w") as file:
                dump({"status_code": status, "content": content}, file)

        # Check for HTTP error status codes (>= 400)
        if status >= 400:
            # Try to parse error JSON (new API format)
            parsed_error = None
            error_msg = None
            error_code = None
            correlation_id = None
            error_path = None

            try:
                parsed_error = loads(content)
                error_msg = parsed_error.get("message")
                error_code = parsed_error.get("code")
                correlation_id = parsed_error.get("correlationId")
                error_path = parsed_error.get("path")
            except (JSONDecodeError, AttributeError):
                pass

            # Build error message
            if error_msg:
                msg = error_msg
            else:
                # Fallback to extracting text from HTML if present
                if "<" in content and ">" in content:
                    matches = re.search("<[^>]+>(.*?)<\\/[^>]+>", content)
                    if matches:
                        inner_text = matches.group(1)
                        msg = re.sub(" GKey\\s*=\\s*[a-f0-9-]+", "", inner_text)
                    else:
                        msg = "HTTP error"
                else:
                    msg = "HTTP error"

            # Build detail string
            detail_parts = [f"status={status}"]
            if error_code:
                detail_parts.append(f"code={error_code}")
            if correlation_id:
                detail_parts.append(f"correlationId={correlation_id}")
            if error_path:
                detail_parts.append(f"path={error_path}")
            detail_parts.append(f"resource={resource}")

            err_message = f"{msg} {' '.join(detail_parts)}"

            if attempt < times - 1:
                sleep(5 ** (attempt + 1))
            else:
                raise ValueError(err_message)

        # Success: try to parse JSON first
        else:
            # Check content-type header if available
            content_type = ""
            if response is not None:
                content_type = response.headers.get("content-type", "")

            # Try to parse JSON first
            try:
                json_parsed = loads(content)
                return json_parsed
            except JSONDecodeError:
                # JSON parsing failed - check if it's HTML (legacy API error format)
                if "<" in content and ">" in content:
                    matches = re.search("<[^>]+>(.*?)<\\/[^>]+>", content)
                    inner_text = matches.group(1) if matches else content
                    output_string = re.sub(" GKey\\s*=\\s*[a-f0-9-]+", "", inner_text)

                    if "Rejected" in content or "Bandwidth" in content:
                        err_message = (
                            f"API request failed. URL: '{url}' "
                            f"Status: '{status}', "
                            f"Content: '{output_string}'\n\n"
                            "API may be overwhelmed by too many "
                            "requests. Take a break and try again."
                        )
                    elif "Service" in content:
                        err_message = (
                            f"API request failed. URL: '{url}' "
                            f"Status: '{status}', "
                            f"Content: '{output_string}'\n\n"
                            "Your requested dataset may be too large. "
                            "Try narrowing your request and try again."
                        )
                    else:
                        err_message = (
                            f"API request failed. URL: '{url}' "
                            f"Status: '{status}', "
                            f"Content: '{output_string}'"
                        )

                    if attempt < times - 1:
                        sleep(5 ** (attempt + 1))
                    else:
                        raise ValueError(err_message)
                else:
                    # Not HTML, but JSON parsing failed
                    if content_type and "json" not in content_type.lower():
                        preview = content[:300]
                        raise ValueError(
                            f"Unexpected content type '{content_type}'. "
                            f"Expected JSON. Resource={resource}. "
                            f"Body preview: {preview}"
                        )
                    elif attempt < times - 1:
                        sleep(5 ** (attempt + 1))
                    else:
                        preview = content[:300]
                        raise ValueError(
                            f"Content from API could not be parsed as JSON. "
                            f"URL: '{url}' Status: '{status}', "
                            f"Content preview: {preview}"
                        )


def _load_cached_response(URL):
    file_name = hashlib.sha256(URL.encode()).hexdigest()
    file_path = f"tests/responses/{file_name}.json"

    if path.exists(file_path):
        with open(file_path, "r") as file:
            data = load(file)
            return data.get("status_code"), data.get("content")
    return None, None


def _extract_first(value):
    """Extract first element from list, or return value if not a list.

    This matches R's [[1]] behavior for extracting scalar values from lists.
    """
    if isinstance(value, list) and len(value) > 0:
        return value[0]
    return value


def _parse_datastructure_urn(urn: str) -> dict[str, Optional[str]]:
    """Parse a datastructure URN into its components.

    Matches the R implementation exactly.

    Example: "urn:sdmx:org.sdmx.infomodel.datastructure.DataStructure=IMF:DSD(1.0)"
    Returns: {"agency": "IMF", "id": "DSD", "version": "1.0"}
    """
    # Pattern matches R: ^urn:sdmx:org\.sdmx\.infomodel\.datastructure\.DataStructure=([^:]+):([^\(]+)\(([^\)]+)\)$
    pattern = (
        r"^urn:sdmx:org\.sdmx\.infomodel\.datastructure\.DataStructure="
        r"([^:]+):([^\(]+)\(([^\)]+)\)$"
    )
    match = re.match(pattern, urn)
    if match:
        return {
            "agency": match.group(1),
            "id": match.group(2),
            "version": match.group(3),
        }
    # Return None values on failure (matching R's behavior)
    return {
        "agency": None,
        "id": None,
        "version": None,
    }


def _parse_concept_urn(urn: str) -> dict[str, Optional[str]]:
    """Parse a concept URN into its components.

    Example: "urn:sdmx:org.sdmx.infomodel.conceptscheme.Concept=IMF:CS_CONCEPT(1.0).CONCEPT_NAME"
    Returns: {"agency": "IMF", "scheme": "CS_CONCEPT", "version": "1.0", "concept": "CONCEPT_NAME"}
    """
    # Pattern matches R: ^urn:sdmx:org\.sdmx\.infomodel\.conceptscheme\.Concept=([^:]+):([^\(]+)\(([^\)]+)\)\.(.+)$
    pattern = (
        r"^urn:sdmx:org\.sdmx\.infomodel\.conceptscheme\.Concept="
        r"([^:]+):([^\(]+)\(([^\)]+)\)\.(.+)$"
    )
    match = re.match(pattern, urn)
    if match:
        return {
            "agency": match.group(1),
            "scheme": match.group(2),
            "version": match.group(3),
            "concept": match.group(4),
        }
    # Return None values on failure (matching R's behavior)
    return {
        "agency": None,
        "scheme": None,
        "version": None,
        "concept": None,
    }


def _parse_codelist_urn(urn: str) -> dict[str, Optional[str]]:
    """Parse a codelist URN into its components.

    Matches the R implementation exactly.

    Example: "urn:sdmx:org.sdmx.infomodel.codelist.Codelist=IMF:CL_FREQ(1.0)"
    Returns: {"agency": "IMF", "id": "CL_FREQ", "version": "1.0"}
    """
    # Pattern matches R: ^urn:sdmx:org\.sdmx\.infomodel\.codelist\.(?:CodeList|Codelist)=([^:]+):([^\(]+)\(([^\)]+)\)$
    pattern = (
        r"^urn:sdmx:org\.sdmx\.infomodel\.codelist\.(?:CodeList|Codelist)="
        r"([^:]+):([^\(]+)\(([^\)]+)\)$"
    )
    match = re.match(pattern, urn)
    if match:
        return {
            "agency": match.group(1),
            "id": match.group(2),
            "version": match.group(3),
        }
    # Return None values on failure (matching R's behavior)
    return {
        "agency": None,
        "id": None,
        "version": None,
    }


def _get_datastructure_components(dataflow_id: str, times: int = 3) -> dict:
    """
    (Internal) Retrieve raw datastructure components for a dataflow.

    This function:
    1. Gets the dataflow to find its structure URN
    2. Parses the structure URN to get agency and ID
    3. Fetches the DSD (datastructure definition)
    4. Returns the dataStructureComponents

    Args:
        dataflow_id (str): The ID of the dataflow (database_id).
        times (int, optional): The number of times to retry the request.
            Defaults to 3.

    Returns:
        dict: The dataStructureComponents dictionary containing dimensionList,
            measureList, etc.
    """
    # Step 1: Get dataflow to find its structure URN
    raw_dl = _download_parse("structure/dataflow/all/*/+", times=times)
    raw_dataflows = raw_dl.get("data", {}).get("dataflows")
    if raw_dataflows is None:
        raise ValueError("No dataflows found in API response.")

    # Find the matching dataflow
    flow_row = None
    for flow in raw_dataflows:
        flow_id = _extract_first(flow.get("id"))
        if flow_id == dataflow_id:
            flow_row = flow
            break

    if flow_row is None:
        raise ValueError(f"Dataflow not found or not unique: {dataflow_id}.")

    # Extract structure URN
    structure_urn = _extract_first(flow_row.get("structure"))
    if not structure_urn:
        raise ValueError(f"Invalid structure URN for dataflow {dataflow_id}.")

    # Step 2: Parse structure URN
    dsd_ref = _parse_datastructure_urn(structure_urn)
    if not dsd_ref.get("agency") or not dsd_ref.get("id"):
        raise ValueError(
            f"Invalid structure URN for dataflow {dataflow_id}: {structure_urn}"
        )

    # Step 3: Fetch DSD
    dsd_path = f"structure/datastructure/{dsd_ref['agency']}/{dsd_ref['id']}/+"
    dsd_body = _download_parse(dsd_path, times=times)

    dsds = dsd_body.get("data", {}).get("dataStructures")
    if not dsds or len(dsds) < 1:
        raise ValueError(f"No dataStructures found in DSD response for {dataflow_id}.")

    # Step 4: Extract components
    components = dsds[0].get("dataStructureComponents")
    if components is None:
        raise ValueError(f"No dataStructureComponents found in DSD for {dataflow_id}.")

    return components


def _imf_dimensions(database_id, times=3, inputs_only=True):
    """
    (Internal) Retrieve the list of codes for dimensions of an individual IMF
    database.

    Args:
        database_id (str): The ID of the IMF database (dataflow_id).
        times (int, optional): The number of times to retry the request in case
        of failure. Defaults to 3.
        inputs_only (bool, optional): If True, only include input parameters.
        Defaults to True.

    Returns:
        pandas.DataFrame: A DataFrame containing the parameter names and their
        corresponding codes and descriptions.
    """
    # Get DSD components
    components = _get_datastructure_components(database_id, times)

    # Extract dimensions from dimensionList
    dimension_list = components.get("dimensionList", {})
    dimensions = dimension_list.get("dimensions", [])
    time_dimensions = dimension_list.get("timeDimensions", [])

    # Extract measures from measureList (only when inputs_only=False)
    measures = []
    if not inputs_only:
        measure_list = components.get("measureList", {})
        measures = measure_list.get("measures", [])

    # Combine dimensions (always), time dimensions (only if inputs_only=False),
    # and measures (only if inputs_only=False)
    dims_to_process = []
    time_dim_ids = set()
    measure_ids = set()

    # Regular dimensions
    for d in dimensions:
        if d is not None:
            dims_to_process.append(("dimension", d))

    # Time dimensions (only if inputs_only=False)
    if not inputs_only:
        for d in time_dimensions:
            if d is not None:
                dim_id = _extract_first(d.get("id"))
                if dim_id:
                    time_dim_ids.add(dim_id)
                dims_to_process.append(("time_dimension", d))

        # Measures (only if inputs_only=False)
        for d in measures:
            if d is not None:
                dim_id = _extract_first(d.get("id"))
                if dim_id:
                    measure_ids.add(dim_id)
                dims_to_process.append(("measure", d))

    if not dims_to_process:
        raise ValueError(f"No dimensions found for database {database_id}.")

    # Build dimension map: dimension_id -> conceptIdentity, local enumeration, and type
    dim_map = {}
    for source_type, dim in dims_to_process:
        dim_id = _extract_first(dim.get("id"))
        concept_identity = _extract_first(dim.get("conceptIdentity"))
        dim_type = _extract_first(dim.get("type"))
        local_enum = None
        try:
            local_rep = dim.get("localRepresentation", {})
            if local_rep:
                local_enum = _extract_first(local_rep.get("enumeration"))
        except (AttributeError, KeyError, TypeError):
            pass

        dim_map[dim_id] = {
            "concept_identity": concept_identity,
            "local_enum": local_enum,
            "type": dim_type,
            "is_time_dimension": dim_id in time_dim_ids,
            "is_measure": dim_id in measure_ids,
        }

    # For each dimension, resolve its codelist and get codes
    params = []
    codes = []
    agencies = []
    descriptions = []

    for dim_id, dim_info in dim_map.items():
        concept_identity = dim_info["concept_identity"]
        local_enum = dim_info["local_enum"]
        dim_type = dim_info["type"]
        is_time_dimension = dim_info["is_time_dimension"]
        is_measure = dim_info["is_measure"]

        # Try to resolve codelist for this dimension/measure
        codelist_id = None
        codelist_agency = None
        codelist_name = None

        if concept_identity:
            # Parse concept URN to get concept scheme info
            cref = _parse_concept_urn(concept_identity)
            if cref.get("agency") and cref.get("scheme") and cref.get("concept"):
                # Fetch concept scheme to find enumeration
                cs_paths = [
                    f"structure/conceptscheme/{cref['agency']}/{cref['scheme']}/+",
                    f"structure/conceptscheme/all/{cref['scheme']}/+",
                ]

                cs_body = None
                for cs_path in cs_paths:
                    try:
                        cs_body = _download_parse(cs_path, times=times)
                        break
                    except ValueError:
                        continue

                if cs_body is not None:
                    # Find the concept in the concept scheme
                    cs_list = cs_body.get("data", {}).get("conceptSchemes", [])
                    concept = None
                    for cs in cs_list:
                        cands = cs.get("concepts", [])
                        if not cands:
                            continue
                        for cn in cands:
                            cn_id = _extract_first(cn.get("id"))
                            if cn_id == cref["concept"]:
                                concept = cn
                                break
                        if concept:
                            break

                    # Get enumeration from concept or fall back to local enum
                    enum_from_concept = None
                    if concept:
                        core_rep = concept.get("coreRepresentation", {})
                        if core_rep:
                            enum_from_concept = _extract_first(
                                core_rep.get("enumeration")
                            )

                    enum_urn = enum_from_concept if enum_from_concept else local_enum
                else:
                    # If concept scheme not found, try local enum directly
                    enum_urn = local_enum
            else:
                # If concept URN parsing fails, try to use local enum directly
                enum_urn = local_enum

            # Try to parse and fetch codelist if we have an enum URN
            if enum_urn:
                cl = _parse_codelist_urn(enum_urn)
                if cl.get("agency") and cl.get("id"):
                    # Fetch codelist - try agency-specific path first to get the correct version,
                    # then fall back to 'all' if the agency path fails
                    cl_paths = [
                        f"structure/codelist/{cl['agency']}/{cl['id']}/+",
                        f"structure/codelist/all/{cl['id']}/+",
                    ]

                    cl_body = None
                    for cl_path in cl_paths:
                        try:
                            cl_body = _download_parse(cl_path, times=times)
                            break
                        except ValueError:
                            continue

                    if cl_body is not None:
                        clists = cl_body.get("data", {}).get("codelists", [])
                        if clists and len(clists) > 0:
                            codes_list = clists[0].get("codes", [])
                            if codes_list:
                                # Extract codelist ID and agency for the code column
                                codelist_id = cl["id"]
                                codelist_agency = cl["agency"]

                                # Get codelist name/description from codelist metadata
                                codelist_name = _extract_first(clists[0].get("name"))
                                if not codelist_name:
                                    # Fallback to codelist ID if no name available
                                    codelist_name = codelist_id

        # Add parameter (always add, even if no codelist found)
        # For inputs_only=True, skip dimensions without codelists
        # For inputs_only=False, include all dimensions/measures even without codelists
        if inputs_only and codelist_id is None:
            continue

        # For time dimensions and measures without codelists, use their ID as the code
        # but leave description as None (this matches the expected behavior where
        # only descriptions are NA, not codes)
        if codelist_id is None and not inputs_only:
            # Check if this is a time dimension or measure
            if (
                is_time_dimension
                or is_measure
                or dim_type in ("TimeDimension", "Measure")
            ):
                codelist_id = dim_id.lower()
                # Ensure description is None (not a string)
                codelist_name = None

        params.append(dim_id.lower())
        codes.append(codelist_id)
        agencies.append(codelist_agency)
        descriptions.append(codelist_name)

    # Build DataFrames
    param_code_df = DataFrame({"parameter": params, "code": codes, "agency": agencies})

    # Create codelist description DataFrame
    # Filter out None codes before creating codelist_df to avoid duplicates with None
    codelist_df = DataFrame(
        {
            "code": [c for c in codes if c is not None],
            "description": [d for c, d in zip(codes, descriptions) if c is not None],
        }
    )
    # Remove duplicates while preserving order
    codelist_df = codelist_df.drop_duplicates(subset=["code"], keep="first")

    # Use left join to keep all parameters and fill in descriptions where available
    result_df = param_code_df.merge(codelist_df, on="code", how="left")

    return result_df


def _imf_metadata(database_id, times=3):
    """
    (Internal) Access metadata for a dataset.

    Args:
        database_id (str): The ID of the IMF database (dataflow_id).
        times (int, optional): Maximum number of requests to attempt. Defaults
        to 3.

    Returns:
        dict: A dictionary containing the metadata information.

    Raises:
        ValueError: If the database_id is not provided.

    Examples:
        # Find Primary Commodity Price System database metadata
        metadata = _imf_metadata("PCPS")
    """

    if not database_id:
        raise ValueError("Must supply database_id.")

    # Get all dataflows to find the matching one
    raw_dl = _download_parse("structure/dataflow/all/*/+", times=times)
    raw_dataflows = raw_dl.get("data", {}).get("dataflows")
    if raw_dataflows is None:
        raise ValueError("No dataflows found in API response.")

    # Find the matching dataflow
    flow_row = None
    for flow in raw_dataflows:
        flow_id = _extract_first(flow.get("id"))
        if flow_id == database_id:
            flow_row = flow
            break

    if flow_row is None:
        raise ValueError(f"Dataflow not found: {database_id}.")

    # Extract agency ID and version for detailed metadata query
    agency_id = _extract_first(flow_row.get("agencyID"))

    # Get detailed metadata from the specific dataflow
    dataflow_path = f"structure/dataflow/{agency_id}/{database_id}/+"
    detailed_response = _download_parse(dataflow_path, times=times)

    # Extract metadata from response
    meta = detailed_response.get("meta", {})
    dataflows = detailed_response.get("data", {}).get("dataflows", [])
    dataflow = dataflows[0] if dataflows else {}

    # Find lastUpdatedAt from annotations
    last_updated = None
    annotations = dataflow.get("annotations", [])
    for ann in annotations:
        if ann.get("id") == "lastUpdatedAt":
            last_updated = ann.get("value")
            break

    # Build output similar to old format but adapted for new API
    output = {
        "schema": meta.get("schema"),
        "message_id": meta.get("id"),
        "language": _extract_first(meta.get("contentLanguages", [])),
        "timestamp": meta.get("prepared"),
        "last_updated": last_updated,
        "database_id": _extract_first(dataflow.get("id")),
        "database_name": _extract_first(dataflow.get("name")),
        "description": _extract_first(dataflow.get("description")),
        "version": _extract_first(dataflow.get("version")),
        "agency_id": _extract_first(dataflow.get("agencyID")),
    }
    return output
