import logging
import pytest
import time
import pandas as pd
import os
from imfp import (
    _imf_get,
    _download_parse,
    _imf_metadata,
    _imf_dimensions,
    set_imf_wait_time,
)
from imfp.utils import _imf_save_response, _imf_use_cache

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


# Set test configuration options
create_cache = False
use_cache = False
wait_time = 0


@pytest.fixture
def set_options(monkeypatch):
    # Store the original values of the options
    original_save_response = _imf_save_response
    original_use_cache = _imf_use_cache
    original_wait_time = os.environ.get("IMF_WAIT_TIME", None)

    # Set caching options for tests
    os.makedirs("tests/responses", exist_ok=True)
    monkeypatch.setattr("imfp.utils._imf_save_response", create_cache)
    monkeypatch.setattr("imfp.utils._imf_use_cache", use_cache)
    set_imf_wait_time(wait_time)

    # Perform the test
    yield float(os.environ.get("IMF_WAIT_TIME"))

    # Restore the original values of the options during teardown
    monkeypatch.setattr("imfp.utils._imf_save_response", original_save_response)
    monkeypatch.setattr("imfp.utils._imf_use_cache", original_use_cache)
    if original_wait_time is not None:
        os.environ["IMF_WAIT_TIME"] = original_wait_time
    else:
        os.environ.pop("IMF_WAIT_TIME", None)


@pytest.fixture
def env_setup_teardown():
    # Store the original value of the environment variable
    original_value = os.environ.get("IMF_WAIT_TIME", None)

    # Set the environment variable for the test
    os.environ["IMF_WAIT_TIME"] = "2.5"

    # Perform the test
    yield original_value

    # Restore the original value of the environment variable after the test
    if original_value is not None:
        os.environ["IMF_WAIT_TIME"] = original_value
    else:
        os.environ.pop("IMF_WAIT_TIME", None)


def test_imf_get(env_setup_teardown, use_saved_responses):
    # Check if the new value is larger than the default value (1.5) or the original value if it exists
    original_value = env_setup_teardown
    if original_value:
        assert float(original_value) <= float(os.environ["IMF_WAIT_TIME"])
    else:
        assert 1.5 <= float(os.environ["IMF_WAIT_TIME"])

    # Use a real URL for testing rate limiting
    test_url = "https://example.com/"
    test_header = {"Accept": "application/json", "User-Agent": "imfp"}

    # Call the _imf_get function
    response = _imf_get(test_url, test_header)
    assert response.status_code == 200

    # Test the rate-limiting functionality by checking the elapsed time
    # between two requests
    start_time = time.perf_counter()
    _imf_get(test_url, test_header)
    _imf_get(test_url, test_header)
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time

    # The elapsed time should be at least the minimum set in the environ variable
    assert elapsed_time >= float(os.environ["IMF_WAIT_TIME"])


def test_download_parse(set_options, use_saved_responses):
    assert (wait_time - 0.1) < set_options < (wait_time + 0.1)

    # Test with a valid new API resource path
    # TODO: Use a path that returns a smaller response
    valid_resource = "structure/dataflow/all/*/+"
    valid_result = _download_parse(valid_resource)
    assert isinstance(valid_result, dict)
    assert "data" in valid_result
    assert "dataflows" in valid_result["data"]

    # Test with an invalid resource path
    invalid_resource = "structure/dataflow/all/not_a_real_database/+"
    with pytest.raises(ValueError):
        _download_parse(invalid_resource)


def test_imf_metadata_valid_database_id(set_options, use_saved_responses):
    assert (wait_time - 0.1) < set_options < (wait_time + 0.1)

    database_id = "PCPS"
    metadata = _imf_metadata(database_id)

    assert isinstance(metadata, dict)
    assert len(metadata) == 10
    # Check that key fields are present and not None
    assert metadata["database_id"] == "PCPS"
    assert metadata["database_name"] is not None
    assert metadata["description"] is not None
    assert metadata["version"] is not None
    assert metadata["agency_id"] is not None
    assert metadata["timestamp"] is not None
    assert metadata["language"] is not None


def test_imf_metadata_invalid_database_id(set_options, use_saved_responses):
    assert (wait_time - 0.1) < set_options < (wait_time + 0.1)

    database_id = "not_a_real_database"

    with pytest.raises(ValueError) as excinfo:
        _imf_metadata(database_id)

    assert "Dataflow not found" in str(excinfo.value)


def test_imf_metadata_empty_database_id(set_options, use_saved_responses):
    assert (wait_time - 0.1) < set_options < (wait_time + 0.1)

    database_id = ""

    with pytest.raises(ValueError) as excinfo:
        _imf_metadata(database_id)

    assert "Must supply database_id" in str(excinfo.value)


def test_imf_dimensions_valid_database_id(set_options, use_saved_responses):
    assert (wait_time - 0.1) < set_options < (wait_time + 0.1)

    database_id = "PCPS"
    dimensions = _imf_dimensions(database_id)

    assert isinstance(dimensions, pd.DataFrame)
    assert dimensions.shape == (4, 4)
    assert dimensions.isna().sum().sum() == 0


def test_imf_dimensions_invalid_database_id(set_options, use_saved_responses):
    assert (wait_time - 0.1) < set_options < (wait_time + 0.1)

    database_id = "not_a_real_database_id"

    with pytest.raises(Exception):
        _imf_dimensions(database_id)


def test_imf_dimensions_times_param(set_options, use_saved_responses):
    assert (wait_time - 0.1) < set_options < (wait_time + 0.1)

    database_id = "PCPS"
    dimensions = _imf_dimensions(database_id, times=2)

    assert isinstance(dimensions, pd.DataFrame)
    assert dimensions.shape == (4, 4)
    assert dimensions.isna().sum().sum() == 0


def test_imf_dimensions_inputs_only_param(set_options, use_saved_responses):
    assert (wait_time - 0.1) < set_options < (wait_time + 0.1)

    database_id = "PCPS"
    dimensions_1 = _imf_dimensions(database_id, inputs_only=True)
    dimensions_2 = _imf_dimensions(database_id, inputs_only=False)

    assert isinstance(dimensions_1, pd.DataFrame)
    assert isinstance(dimensions_2, pd.DataFrame)
    assert dimensions_1.shape == (4, 4)
    assert dimensions_2.shape == (6, 4)
    assert dimensions_1.isna().sum().sum() == 0
    assert dimensions_2.isna().sum().sum() == 4
