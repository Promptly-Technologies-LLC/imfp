import hashlib
import logging
import re
from collections.abc import Callable
from json import JSONDecodeError, dump, load, loads
from os import environ, path
from time import perf_counter, sleep
from typing import Any, Literal, ParamSpec, TypeVar
from urllib.parse import urljoin, urlparse
from warnings import warn

from pandas import DataFrame
from requests import Response, get

logger = logging.getLogger(__name__)

# New IMF API base URL
IMF_API_BASE_URL = "https://api.imf.org/external/sdmx/3.0/"

P = ParamSpec("P")
R = TypeVar("R")


def _min_wait_time_limited(
    default_wait_time: float = 1.5,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        last_called = [0.0]

        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
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
def _imf_get(
    url: str, headers: dict[str, str], timeout: float | None = None
) -> Response:
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
    resource_or_url: str,
    times: int = 3,
    base_url: str | None = None,
    query_params: dict[str, Any] | None = None,
    timeout_seconds: float = 30.0,
    low_speed_seconds: float = 15.0,
) -> dict[str, Any]:
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
                status = 0 if cached_status is None else cached_status
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

    raise ValueError(
        f"Content from API could not be parsed as JSON. Resource={resource}."
    )


def _load_cached_response(URL: str) -> tuple[int | None, str | None]:
    file_name = hashlib.sha256(URL.encode()).hexdigest()
    file_path = f"tests/responses/{file_name}.json"

    if path.exists(file_path):
        with open(file_path) as file:
            data = load(file)
            return data.get("status_code"), data.get("content")
    return None, None


def _extract_first(value: Any) -> Any:
    """Extract first element from list, or return value if not a list.

    This matches R's [[1]] behavior for extracting scalar values from lists.
    """
    if isinstance(value, list) and len(value) > 0:
        return value[0]
    return value


def _parse_datastructure_urn(urn: str) -> dict[str, str | None]:
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


def _parse_concept_urn(urn: str) -> dict[str, str | None]:
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


def _parse_codelist_urn(urn: str) -> dict[str, str | None]:
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


def _get_dataflow_rows(times: int = 3) -> list[dict[str, Any]]:
    """
    (Internal) Fetch the raw list of dataflow objects from the IMF catalog.

    Args:
        times (int, optional): The number of times to retry the request.
            Defaults to 3.

    Returns:
        list: Raw dataflow dictionaries as returned by the API.

    Raises:
        ValueError: If the response contains no dataflows.
    """
    raw_dl = _download_parse("structure/dataflow/all/*/+", times=times)
    raw_dataflows = raw_dl.get("data", {}).get("dataflows")
    if raw_dataflows is None:
        raise ValueError("No dataflows found in API response.")
    return raw_dataflows


def _find_dataflow(dataflow_id: str, times: int = 3) -> dict[str, Any]:
    """
    (Internal) Look up a dataflow object by ID from the IMF dataflow catalog.

    Args:
        dataflow_id (str): The ID of the dataflow (database_id).
        times (int, optional): The number of times to retry the request.
            Defaults to 3.

    Returns:
        dict: The matching dataflow object from the API response.
    """
    for flow in _get_dataflow_rows(times=times):
        if _extract_first(flow.get("id")) == dataflow_id:
            return flow

    raise ValueError(f"Dataflow not found or not unique: {dataflow_id}.")


def _annotation_value(obj: dict[str, Any], annotation_id: str) -> str | None:
    """Return the value of a named annotation on an SDMX artefact, if present."""
    for annotation in obj.get("annotations", []) or []:
        if annotation.get("id") == annotation_id:
            return annotation.get("value")
    return None


def _get_datastructure_components(
    dataflow_id: str,
    times: int = 3,
    flow_row: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    (Internal) Retrieve raw datastructure components for a dataflow.

    This function:
    1. Gets the dataflow to find its structure URN (or uses a provided flow)
    2. Parses the structure URN to get agency and ID
    3. Fetches the DSD (datastructure definition)
    4. Returns the dataStructureComponents

    Args:
        dataflow_id (str): The ID of the dataflow (database_id).
        times (int, optional): The number of times to retry the request.
            Defaults to 3.
        flow_row (dict, optional): Pre-fetched dataflow object. When provided,
            skips the dataflow catalog request.

    Returns:
        dict: The dataStructureComponents dictionary containing dimensionList,
            measureList, etc.
    """
    if flow_row is None:
        flow_row = _find_dataflow(dataflow_id, times=times)

    # Extract structure URN
    structure_urn = _extract_first(flow_row.get("structure"))
    if not structure_urn:
        raise ValueError(f"Invalid structure URN for dataflow {dataflow_id}.")

    # Parse structure URN
    dsd_ref = _parse_datastructure_urn(structure_urn)
    if not dsd_ref.get("agency") or not dsd_ref.get("id"):
        raise ValueError(
            f"Invalid structure URN for dataflow {dataflow_id}: {structure_urn}"
        )

    # Fetch DSD
    dsd_path = f"structure/datastructure/{dsd_ref['agency']}/{dsd_ref['id']}/+"
    dsd_body = _download_parse(dsd_path, times=times)

    dsds = dsd_body.get("data", {}).get("dataStructures")
    if not dsds or len(dsds) < 1:
        raise ValueError(f"No dataStructures found in DSD response for {dataflow_id}.")

    components = dsds[0].get("dataStructureComponents")
    if components is None:
        raise ValueError(f"No dataStructureComponents found in DSD for {dataflow_id}.")

    return components


def _component_codelist(
    component: dict[str, Any],
    times: int = 3,
    memo: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """
    (Internal) Resolve the codelist that enumerates a datastructure component.

    A component's codelist is normally declared indirectly, via the concept it
    points at through ``conceptIdentity``; some components instead declare it
    inline through ``localRepresentation``. This resolves either form and
    fetches the codelist.

    Args:
        component (dict): A raw dimension, time dimension, or measure object
            from a datastructure definition.
        times (int, optional): The number of times to retry each request.
            Defaults to 3.
        memo (dict, optional): Mutable cache, keyed by URN, shared across calls
            so that dimensions sharing a codelist only trigger one request.

    Returns:
        tuple: ``(ref, codes)``, where ``ref`` is a dict with ``id``, ``agency``,
        ``version``, and ``name`` keys (values are None when unresolved) and
        ``codes`` is the list of raw code objects (empty when unenumerated).
    """
    if memo is None:
        memo = {}

    empty_ref: dict[str, Any] = {
        "id": None,
        "agency": None,
        "version": None,
        "name": None,
    }

    concept_identity = _extract_first(component.get("conceptIdentity"))

    local_enum = None
    local_rep = component.get("localRepresentation") or {}
    if local_rep:
        local_enum = _extract_first(local_rep.get("enumeration"))

    if not concept_identity:
        # Without a concept identity there is nothing to resolve beyond the
        # component's own inline representation.
        enum_urn = local_enum
    else:
        cref = _parse_concept_urn(concept_identity)
        enum_urn = local_enum
        if cref.get("agency") and cref.get("scheme") and cref.get("concept"):
            cs_key = f"conceptscheme:{cref['agency']}:{cref['scheme']}"
            if cs_key in memo:
                cs_body = memo[cs_key]
            else:
                cs_body = None
                for cs_path in (
                    f"structure/conceptscheme/{cref['agency']}/{cref['scheme']}/+",
                    f"structure/conceptscheme/all/{cref['scheme']}/+",
                ):
                    try:
                        cs_body = _download_parse(cs_path, times=times)
                        break
                    except ValueError:
                        continue
                memo[cs_key] = cs_body

            if cs_body is not None:
                concept = None
                for cs in cs_body.get("data", {}).get("conceptSchemes", []):
                    for cn in cs.get("concepts", []) or []:
                        if _extract_first(cn.get("id")) == cref["concept"]:
                            concept = cn
                            break
                    if concept:
                        break

                enum_from_concept = None
                if concept:
                    core_rep = concept.get("coreRepresentation") or {}
                    if core_rep:
                        enum_from_concept = _extract_first(core_rep.get("enumeration"))

                enum_urn = enum_from_concept if enum_from_concept else local_enum

    if not enum_urn:
        return empty_ref, []

    cl = _parse_codelist_urn(enum_urn)
    if not cl.get("agency") or not cl.get("id"):
        return empty_ref, []

    cl_key = f"codelist:{cl['agency']}:{cl['id']}"
    if cl_key in memo:
        cl_body = memo[cl_key]
    else:
        cl_body = None
        # Try the agency-specific path first so we pick up the right version,
        # then fall back to the wildcard agency.
        for cl_path in (
            f"structure/codelist/{cl['agency']}/{cl['id']}/+",
            f"structure/codelist/all/{cl['id']}/+",
        ):
            try:
                cl_body = _download_parse(cl_path, times=times)
                break
            except ValueError:
                continue
        memo[cl_key] = cl_body

    if cl_body is None:
        return empty_ref, []

    clists = cl_body.get("data", {}).get("codelists", [])
    if not clists:
        return empty_ref, []

    codes = clists[0].get("codes", []) or []
    if not codes:
        return empty_ref, []

    return (
        {
            "id": cl["id"],
            "agency": cl["agency"],
            "version": _extract_first(clists[0].get("version")) or cl.get("version"),
            "name": _extract_first(clists[0].get("name")) or cl["id"],
        },
        codes,
    )


def _dsd_component_rows(
    dataflow_id: str,
    times: int = 3,
    include_time: bool = False,
    include_measures: bool = False,
    flow_row: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    (Internal) List a dataflow's datastructure components in positional order.

    Args:
        dataflow_id (str): The ID of the dataflow.
        times (int, optional): The number of times to retry each request.
            Defaults to 3.
        include_time (bool, optional): Whether to include time dimensions.
        include_measures (bool, optional): Whether to include measures.
        flow_row (dict, optional): Pre-fetched dataflow object, to avoid a
            redundant catalog request when the caller already has one.

    Returns:
        list: Dicts with ``dimension_id``, ``type``, ``position``, and the raw
        ``component`` object. Dimensions come first, in DSD position order,
        followed by time dimensions and then measures.
    """
    components = _get_datastructure_components(dataflow_id, times, flow_row=flow_row)
    dimension_list = components.get("dimensionList", {}) or {}

    def _rows(items: list[Any] | None, default_type: str) -> list[dict[str, Any]]:
        collected = []
        for item in items or []:
            if not item:
                continue
            dim_id = _extract_first(item.get("id"))
            if not dim_id:
                continue
            position = item.get("position")
            collected.append(
                {
                    "dimension_id": dim_id,
                    "type": _extract_first(item.get("type")) or default_type,
                    "position": int(position) if position is not None else None,
                    "component": item,
                }
            )
        return collected

    rows = _rows(dimension_list.get("dimensions"), "Dimension")
    # Components without a declared position sort last rather than blowing up.
    rows.sort(key=lambda row: (row["position"] is None, row["position"] or 0))

    if include_time:
        rows.extend(_rows(dimension_list.get("timeDimensions"), "TimeDimension"))

    if include_measures:
        measure_list = components.get("measureList", {}) or {}
        rows.extend(_rows(measure_list.get("measures"), "Measure"))

    if not rows:
        raise ValueError(f"No dimensions found for database {dataflow_id}.")

    return rows


def _imf_dimensions(
    database_id: str, times: int = 3, inputs_only: bool = True
) -> DataFrame:
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
    memo: dict[str, Any] = {}
    rows = _dsd_component_rows(
        database_id,
        times=times,
        include_time=not inputs_only,
        include_measures=not inputs_only,
    )

    params = []
    codes = []
    agencies = []
    descriptions = []
    seen = set()

    for row in rows:
        dim_id = row["dimension_id"]
        if dim_id in seen:
            continue
        seen.add(dim_id)

        ref, _codes = _component_codelist(row["component"], times=times, memo=memo)
        codelist_id = ref["id"]
        codelist_name = ref["name"]

        # Enumerated dimensions are the only ones usable as request filters.
        if inputs_only and codelist_id is None:
            continue

        # Time dimensions and measures are never enumerated; surface them under
        # their own ID so callers can still see that they exist.
        if codelist_id is None and row["type"] in ("TimeDimension", "Measure"):
            codelist_id = dim_id.lower()
            codelist_name = None

        params.append(dim_id.lower())
        codes.append(codelist_id)
        agencies.append(ref["agency"])
        descriptions.append(codelist_name)

    param_code_df = DataFrame({"parameter": params, "code": codes, "agency": agencies})

    # Build the code -> description lookup from enumerated components only, so
    # that unenumerated components do not collide on a None key.
    codelist_df = DataFrame(
        {
            "code": [c for c in codes if c is not None],
            "description": [d for c, d in zip(codes, descriptions) if c is not None],
        }
    )
    codelist_df = codelist_df.drop_duplicates(subset=["code"], keep="first")

    # Left join so parameters without a description are kept.
    result_df = param_code_df.merge(codelist_df, on="code", how="left")

    return result_df


_PERIOD_FREQ_SUFFIX = re.compile(r"^\d{4}-(M|Q|A|W)\d+$")
_PERIOD_MONTH = re.compile(r"^\d{4}-\d{2}$")
_PERIOD_YEAR = re.compile(r"^\d{4}$")


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
    """
    (Internal) Build the query parameters for a data request, including the
    time window when the publishing agency supports server-side filtering.
    """
    query_params = {
        "dimensionAtObservation": "TIME_PERIOD",
        "attributes": "dsd",
        "measures": "all",
    }
    time_filters = []
    if start_period:
        start = _transform_period_for_frequency(
            start_period, user_frequency, bound="start"
        )
        time_filters.append(f"ge:{start}")
    if end_period:
        end = _transform_period_for_frequency(end_period, user_frequency, bound="end")
        time_filters.append(f"le:{end}")
    if time_filters:
        if provider_agency == "IMF.STA":
            query_params["c[TIME_PERIOD]"] = "+".join(time_filters)
        else:
            warn(
                f"Agency {provider_agency} does not support time filters; "
                "time window will be ignored."
            )
    return query_params


def _build_data_request(
    dataflow_id: str,
    dimension_filters: dict[str, list[str]],
    start_period: str | None = None,
    end_period: str | None = None,
    times: int = 3,
    flow_row: dict[str, Any] | None = None,
) -> tuple[str, dict[str, str]]:
    """
    (Internal) Build the resource path and query parameters for a data request.

    The series key is positional: each dimension in the datastructure occupies
    one dot-separated slot, in DSD position order, and a slot is wildcarded with
    ``*`` when the caller supplied no codes for it. Multiple codes for one
    dimension are joined with ``+``.

    Args:
        dataflow_id (str): The ID of the dataflow to query.
        dimension_filters (dict): Maps upper-cased dimension IDs to lists of
            codes. Dimensions absent from the dict are wildcarded.
        start_period (str, optional): Lower bound on the time period.
        end_period (str, optional): Upper bound on the time period.
        times (int, optional): The number of times to retry each request.
        flow_row (dict, optional): Pre-fetched dataflow object. Supplying it
            keeps the whole request to a single catalog lookup.

    Returns:
        tuple: ``(data_path, query_params)``.

    Raises:
        ValueError: If a requested dimension is not part of the datastructure.
    """
    # One catalog lookup serves both DSD resolution and provider agency.
    if flow_row is None:
        flow_row = _find_dataflow(dataflow_id, times=times)

    rows = _dsd_component_rows(dataflow_id, times=times, flow_row=flow_row)
    key_rows = [row for row in rows if row["type"] != "TimeDimension"]

    available_dims = {row["dimension_id"].upper() for row in key_rows}
    unknown = set(dimension_filters) - available_dims
    if unknown:
        raise ValueError(
            f"Unknown dimension(s): {', '.join(sorted(unknown))}. "
            f"Available dimensions: {', '.join(sorted(available_dims))}"
        )

    segments = []
    for row in key_rows:
        codes = dimension_filters.get(row["dimension_id"].upper(), [])
        segments.append("+".join(codes) if codes else "*")
    key = ".".join(segments)

    # A bare year is expanded using the requested frequency, so find whichever
    # frequency dimension this datastructure happens to use.
    freq_dim_id = next((d for d in ("FREQUENCY", "FREQ") if d in available_dims), None)
    user_frequency = dimension_filters.get(freq_dim_id) if freq_dim_id else None

    provider_agency = _extract_first(flow_row.get("agencyID")) or "all"

    query_params = _build_time_query_params(
        start_period, end_period, user_frequency, provider_agency
    )

    return f"data/dataflow/{provider_agency}/{dataflow_id}/+/{key}", query_params


def _parse_imf_sdmx_json(message: dict[str, Any]) -> DataFrame:
    """
    (Internal) Flatten an SDMX-JSON data message into one row per observation.

    The message stores observations under compact numeric keys: a series key
    like ``"0:3:1"`` indexes into each dimension's value list, and each
    observation key indexes into the time dimension's value list. Both are
    expanded back into codes here.

    Args:
        message (dict): The parsed JSON response from the API.

    Returns:
        pandas.DataFrame: One row per observation, with a column per series
        dimension plus TIME_PERIOD and OBS_VALUE. Empty if the message carries
        no observations.
    """
    if not message or not message.get("data"):
        return DataFrame()

    data_sets = message.get("data", {}).get("dataSets")
    structures = message.get("data", {}).get("structures")

    if not data_sets or not structures:
        return DataFrame()

    ds = data_sets[0]
    st = structures[0]

    series_dims = st.get("dimensions", {}).get("series", [])
    obs_dims = st.get("dimensions", {}).get("observation", [])
    obs_dim = obs_dims[0] if obs_dims else None

    def index_to_value(
        dim_def: dict[str, Any] | None, idx: Any, keys: tuple[str, ...]
    ) -> Any:
        """Look up a dimension value by its positional index."""
        if not dim_def or not dim_def.get("values"):
            return None
        try:
            i = int(idx)
        except (ValueError, TypeError):
            return None
        values = dim_def["values"]
        if i < 0 or i >= len(values):
            return None
        entry = values[i]
        for k in keys:
            if entry.get(k) is not None:
                return entry[k]
        return None

    if not ds.get("series"):
        return DataFrame()

    series_dim_ids = [_extract_first(dim.get("id")) for dim in series_dims or []]

    rows = []
    for series_key, series in ds["series"].items():
        observations = series.get("observations", {})
        if not observations:
            continue

        key_parts: list[Any] = series_key.split(":")
        # Pad so a short key still lines up with the dimension list.
        if len(key_parts) < len(series_dim_ids):
            key_parts.extend([None] * (len(series_dim_ids) - len(key_parts)))

        series_codes = [
            index_to_value(dim_def, idx, ("id", "value")) if idx is not None else None
            for dim_def, idx in zip(series_dims or [], key_parts)
        ]

        for obs_key, obs in observations.items():
            raw_value = obs[0] if obs else None
            obs_value = None
            if raw_value is not None:
                try:
                    obs_value = float(raw_value)
                except (ValueError, TypeError):
                    # Non-numeric missing-value flags stay None.
                    obs_value = None

            row = dict(zip(series_dim_ids, series_codes))
            row["TIME_PERIOD"] = index_to_value(obs_dim, obs_key, ("value", "id"))
            row["OBS_VALUE"] = obs_value
            rows.append(row)

    return DataFrame(rows) if rows else DataFrame()


def _imf_metadata(database_id: str, times: int = 3) -> dict[str, Any]:
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

    try:
        flow_row = _find_dataflow(database_id, times=times)
    except ValueError as e:
        if "Dataflow not found" in str(e):
            raise ValueError(f"Dataflow not found: {database_id}.") from e
        raise

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
    last_updated = _annotation_value(dataflow, "lastUpdatedAt")

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
