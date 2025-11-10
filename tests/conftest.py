import pytest
import hashlib
import json
from pathlib import Path
import re
import os


@pytest.fixture
def use_saved_responses():
    """
    Autouse fixture to mock HTTP calls by hashing the request URL and loading the
    corresponding file from tests/responses/<sha256(url)>.json.
    """
    import responses

    rsps = responses.RequestsMock(assert_all_requests_are_fired=False)
    rsps.start()
    try:

        def responder(request):
            url = request.url
            file_name = hashlib.sha256(url.encode()).hexdigest()
            file_path = Path("tests/responses") / f"{file_name}.json"
            if not file_path.exists():
                raise AssertionError(
                    "No cached HTTP fixture found for this request.\n"
                    f"- URL: {url}\n"
                    f"- SHA256(URL): {file_name}\n"
                    f"- Expected file: {file_path}\n\n"
                    "Likely causes:\n"
                    "1) The test is issuing a different URL than expected "
                    "(e.g., query params/base URL differ).\n"
                    "2) A live API response has not been captured yet for this URL.\n\n"
                    "How to resolve:\n"
                    "- First, run the test with the 'capture_all_requests' fixture "
                    "to capture live responses, e.g. add it as a test arg or "
                    "@pytest.mark.usefixtures('capture_all_requests').\n"
                    "- Then re-run with 'use_saved_responses' to use the cached data."
                )
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            status = int(data.get("status_code", 200))
            body = data.get("text") or data.get("content") or ""
            headers = dict(data.get("headers", {}))
            # Remove content-encoding and content-length since body is already decoded
            # (we saved response.text, not the compressed bytes)
            headers.pop("content-encoding", None)
            headers.pop("Content-Encoding", None)
            headers.pop("content-length", None)
            headers.pop("Content-Length", None)
            return (status, headers, body)

        rsps.add_callback(
            responses.GET,
            re.compile(r".*"),
            callback=responder,
        )
        yield
    finally:
        rsps.stop()
        rsps.reset()


@pytest.fixture
def capture_all_requests(monkeypatch):
    """
    Autouse fixture to capture and save all HTTP responses during tests in this file.
    Patches both the locally imported _imf_get and the internal imfp.utils._imf_get.
    """
    import logging
    from time import sleep, perf_counter
    from requests import get

    logger = logging.getLogger(__name__)

    def _min_wait_time_limited(default_wait_time=1.5):
        """Rate limiting decorator matching the one in imfp.utils"""

        def decorator(func):
            last_called = [0.0]

            def wrapper(*args, **kwargs):
                min_wait_time = float(
                    os.environ.get("IMF_WAIT_TIME", default_wait_time)
                )
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
    def _imf_get_and_save(url, headers, timeout=None, output_dir="tests/responses"):
        """
        Identical to _imf_get but saves responses to JSON files for later mocking.

        This function captures all responses automatically, saving them with a hash
        of the URL as the filename. Use this temporarily by patching _imf_get to
        capture responses, then switch back to using the saved responses with mocking.

        Args:
            url (str): The URL to send a GET request to.
            headers (dict): The headers to use in the API request.
            timeout (float, optional): Timeout in seconds for the request.
            output_dir (str): Directory to save response files.

        Returns:
            requests.Response: The response object returned by requests.get.
        """
        logger.debug(f"Sending GET request to {url} (with save)")

        # Make the actual request
        response = get(url, headers=headers, timeout=timeout)

        # Save the response
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        file_name = hashlib.sha256(url.encode()).hexdigest()
        file_path = os.path.join(output_dir, f"{file_name}.json")

        # Capture response data in format suitable for responses library
        response_data = {
            "url": url,
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "text": response.text,
            "encoding": response.encoding,
        }

        # Save to JSON
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(response_data, f, indent=2, ensure_ascii=False)

        logger.debug(f"Saved response to: {file_path}")

        return response

    os.makedirs("tests/responses", exist_ok=True)
    # Patch the local symbol imported at module level in this test file
    monkeypatch.setattr("tests.test_utils._imf_get", _imf_get_and_save)
    # Patch the utils reference used by internal functions like _download_parse
    monkeypatch.setattr("imfp.utils._imf_get", _imf_get_and_save)
    yield
