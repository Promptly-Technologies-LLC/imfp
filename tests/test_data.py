import logging
import pytest
import os
import pandas as pd
from imfp import (
    imf_databases,
    imf_parameters,
    imf_parameter_defs,
    imf_dataset,
    set_imf_wait_time,
)
from imfp.utils import _imf_save_response, _imf_use_cache

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def _freq_key(params: dict) -> str | None:
    if "frequency" in params:
        return "frequency"
    if "freq" in params:
        return "freq"
    return None


# Set test configuration options
create_cache = False
use_cache = False
wait_time = 0


@pytest.fixture
def set_options(monkeypatch):
    # Create the responses directory if it doesn't exist
    os.makedirs("tests/responses", exist_ok=True)

    # Store the original values of the options
    original_save_response = _imf_save_response
    original_use_cache = _imf_use_cache
    original_wait_time = os.environ.get("IMF_WAIT_TIME", None)

    # Set caching options for response mocking
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


def test_imf_databases(set_options, use_saved_responses):
    assert (wait_time - 0.1) < set_options < (wait_time + 0.1)

    result = imf_databases()
    assert isinstance(result, pd.DataFrame), "Result should be a pandas DataFrame"
    expected_column_names = ["database_id", "description"]
    assert (
        list(result.columns) == expected_column_names
    ), "Result should have the expected column names"
    assert result.isna().sum().sum() == 0, "Result should not contain any NAs"
    assert len(result["database_id"]) == len(
        result["description"]
    ), "Both columns should have the same length"


def test_imf_parameter_defs(set_options, use_saved_responses):
    assert (wait_time - 0.1) < set_options < (wait_time + 0.1)

    result = imf_parameter_defs("BOP")
    assert isinstance(result, pd.DataFrame), "Result should be a pandas DataFrame"
    assert result.shape[0] >= 3, "Result should have at least 3 rows"
    assert result.shape[1] == 2, "Result should have 2 columns"
    expected_column_names = ["parameter", "description"]
    assert (
        list(result.columns) == expected_column_names
    ), "Result should have the expected column names"

    result = imf_parameter_defs("BOP", inputs_only=False)
    assert isinstance(result, pd.DataFrame), "Result should be a pandas DataFrame"
    assert result.shape[0] >= 5, "Result should have at least 5 rows"
    assert result.shape[1] == 2, "Result should have 2 columns"
    expected_column_names = ["parameter", "description"]
    assert (
        list(result.columns) == expected_column_names
    ), "Result should have the expected column names"

    with pytest.raises(Exception):
        imf_parameter_defs(times=1)
    with pytest.raises(Exception):
        imf_parameters("not_a_real_database", times=1)


def test_imf_parameters(set_options, use_saved_responses):
    assert (wait_time - 0.1) < set_options < (wait_time + 0.1)

    params = imf_parameters("BOP")
    fk = _freq_key(params)
    assert (
        fk is not None
    ), "Expected a frequency-like parameter in imf_parameters output"
    available = set(params[fk]["input_code"])
    # Under SDMX 3.0, frequency sets may expand. Require at least Annual and Quarterly present.
    assert {"A", "Q"}.issubset(available)
    with pytest.raises(Exception):
        imf_parameters(times=1)
    with pytest.raises(Exception):
        imf_parameters(database_id="not_a_real_database", times=1)


def test_imf_dataset_error_handling(set_options, use_saved_responses):
    assert (wait_time - 0.1) < set_options < (wait_time + 0.1)

    params = imf_parameters("FD")
    fk = _freq_key(params)
    assert (
        fk is not None
    ), "Expected a frequency-like parameter in imf_parameters output"
    # Keep frequency minimal, wildcard everything else to avoid over-restriction
    params[fk] = params[fk].head(1)
    for k in list(params.keys()):
        if k != fk:
            params[k] = params[k].iloc[0:0]
    with pytest.raises(Exception):
        imf_dataset(
            database_id="APDREO",
            counterpart_area="X",
            counterpart_sector="X",
            times=1,
        )
    with pytest.warns(Warning):
        imf_dataset(
            database_id="APDREO", ref_area="AU", indicator=["BCA_BP6_USD", "XYZ"]
        )
    with pytest.raises(Exception):
        imf_dataset(times=1)
    with pytest.raises(Exception):
        imf_dataset(database_id=2, times=1)
    with pytest.raises(Exception):
        imf_dataset(database_id=[], times=1)
    with pytest.raises(Exception):
        imf_dataset(database_id=["a", "b"], times=1)
    with pytest.raises(Exception):
        imf_dataset(database_id="not_a_real_database", times=1)
    with pytest.raises(Exception):
        imf_dataset(database_id="PCPS", start_year=1, times=1)
    with pytest.raises(Exception):
        imf_dataset(database_id="PCPS", end_year="a", times=1)
    with pytest.raises(Exception):
        imf_dataset(database_id="PCPS", end_year=[1999, 2004], times=1)
    with pytest.raises(Exception):
        imf_dataset(
            database_id="WHDREO",
            freq="M",
            ref_area="US",
            indicator=["PPPSH", "NGDPD"],
            start_year=2010,
            end_year=2011,
        )
    with pytest.warns(Warning):
        imf_dataset(
            database_id="FD",
            parameters=params,
            ref_sector=["1C_CG", "1C_LG"],
        )
    # In SDMX 3.0, invalid ref_area may be ignored (wildcarded) with a warning instead of error
    with pytest.warns(Warning):
        imf_dataset(
            database_id="BOP",
            freq="A",
            ref_area="AF",
            start_year=2016,
            end_year=2018,
        )


def test_imf_dataset_params_list_request(set_options, use_saved_responses):
    assert (wait_time - 0.1) < set_options < (wait_time + 0.1)

    # Known-good GFS_SOO parameter set (ISO-3 country code)
    df = imf_dataset(
        database_id="GFS_SOO",
        country="ABW",
        sector="S13",
        gfs_grp="G2M",
        indicator=["G23_T"],
        type_of_transformation="POGDP_PT",
        freq="A",
        start_year=1972,
        end_year=1976,
    )
    assert len(df) > 0
    assert "time_period" in df.columns
    for col in [
        "country",
        "sector",
        "gfs_grp",
        "indicator",
        "type_of_transformation",
        "frequency",
        "obs_value",
    ]:
        assert col in df.columns


def test_imf_dataset_vector_parameters_request(set_options, use_saved_responses):
    assert (wait_time - 0.1) < set_options < (wait_time + 0.1)

    df = imf_dataset(
        database_id="AFRREO",
        indicator=["TTT_IX", "GGX_G01_GDP_PT"],
        start_year=2021,
    )
    assert len(df) > 1
    # Some agencies ignore time filters; only assert column existence
    assert "time_period" in df.columns
    assert all(
        indicator in ["TTT_IX", "GGX_G01_GDP_PT"] for indicator in df["indicator"]
    )


def test_imf_dataset_data_frame_prep(set_options, use_saved_responses):
    assert (wait_time - 0.1) < set_options < (wait_time + 0.1)

    # Use confirmed working WHDREO parameters (A, GX1213, BCA_GDP_BP6)
    wh_country = "GX1213"
    wh_inds = ["BCA_GDP_BP6"]

    case_1 = imf_dataset(
        database_id="WHDREO",
        freq="A",
        country=wh_country,
        indicator=wh_inds,
        start_year=2010,
        end_year=2012,
    )
    case_2 = imf_dataset(
        database_id="WHDREO",
        freq="A",
        country=wh_country,
        indicator=wh_inds,
        start_year=2010,
        end_year=2011,
    )
    case_3 = imf_dataset(
        database_id="WHDREO",
        freq="A",
        country=wh_country,
        indicator=[wh_inds[0]] if wh_inds else [],
        start_year=2011,
        end_year=2012,
    )

    desired_names = ["time_period", "obs_value", "frequency", "country", "indicator"]

    # SDMX 3.0 time filters may be ignored for non-IMF.STA agencies; relax row count expectations
    assert len(case_1) >= 4 and len(case_2) >= 2 and len(case_3) >= 2
    assert (
        len(case_1.columns) == 5
        and len(case_2.columns) == 5
        and len(case_3.columns) == 5
    )
    assert (
        all(col in desired_names for col in case_1.columns)
        and all(col in desired_names for col in case_2.columns)
        and all(col in desired_names for col in case_3.columns)
    )


def test_imf_dataset_include_metadata(set_options, use_saved_responses):
    assert (wait_time - 0.1) < set_options < (wait_time + 0.1)

    # Use confirmed working WHDREO parameters (A, GX1213, BCA_GDP_BP6)
    wh_country = "GX1213"
    wh_inds = ["BCA_GDP_BP6"]

    output = imf_dataset(
        database_id="WHDREO",
        freq="A",
        country=wh_country,
        indicator=wh_inds,
        start_year=2010,
        end_year=2012,
        include_metadata=True,
    )
    assert isinstance(output, tuple)
    assert len(output) == 2
    assert isinstance(output[0], dict)
    assert isinstance(output[1], pd.core.frame.DataFrame)
    assert all([not pd.isna(value) for value in output[0].values()])


def test_imf_parameters_returns_iso3_codes_for_gfs_soo(
    set_options, use_saved_responses
):
    """Test that imf_parameters returns ISO3 country codes for GFS_SOO database.

    This test ensures that we're getting the correct codelist from the IMF agency,
    which uses ISO3 codes (e.g., AFG, ALB, DZA) rather than numeric codes (e.g., 512, 799, 914).
    """
    assert (wait_time - 0.1) < set_options < (wait_time + 0.1)

    params = imf_parameters("GFS_SOO")

    # GFS_SOO should have a 'country' parameter
    assert "country" in params, "GFS_SOO should have a 'country' parameter"

    country_df = params["country"]

    # Should have input_code and description columns
    assert "input_code" in country_df.columns
    assert "description" in country_df.columns

    # Get all country codes
    country_codes = list(country_df["input_code"])

    # Should have a reasonable number of countries (IMF has data for many countries)
    assert (
        len(country_codes) > 100
    ), f"Expected more than 100 countries, got {len(country_codes)}"

    # Check for known ISO3 codes that should be present
    expected_iso3_codes = [
        "AFG",
        "ALB",
        "DZA",
        "ASM",
        "AND",
        "AGO",
        "AIA",
        "ATG",
        "ARG",
        "ARM",
    ]
    for code in expected_iso3_codes:
        assert (
            code in country_codes
        ), f"Expected ISO3 code '{code}' not found in country codes"

    # Check that we're NOT getting numeric codes (which would be wrong)
    numeric_codes = [code for code in country_codes if code.isdigit()]
    assert (
        len(numeric_codes) == 0
    ), f"Found unexpected numeric codes: {numeric_codes[:10]}"

    # Verify that most codes are 3-letter codes (ISO3 standard)
    # Note: IMF includes some non-standard codes (e.g., regional aggregates), so we use 70% threshold
    three_letter_codes = [
        code for code in country_codes if len(code) == 3 and code.isalpha()
    ]
    assert (
        len(three_letter_codes) > len(country_codes) * 0.7
    ), f"Expected most codes to be 3-letter ISO codes, but only {len(three_letter_codes)}/{len(country_codes)} are"
