"""Tests for the econdataverse-style API in imfp.api.

Like the rest of the suite these run fully offline: conftest's
``use_saved_responses`` fixture replays cached JSON keyed by the SHA256 of the
request URL, so a test that changes the URL a function builds will fail loudly
rather than hit the network.
"""

import os
import warnings

import pandas as pd
import pytest

from imfp import (
    imf_databases,
    imf_dataset,
    imf_get,
    imf_get_codelists,
    imf_get_dataflows,
    imf_get_datastructure,
    imf_parameter_defs,
    imf_parameters,
    set_imf_wait_time,
)
from imfp.utils import _imf_save_response, _imf_use_cache


@pytest.fixture
def set_options(monkeypatch):
    """Disable rate limiting and response capture for the duration of a test."""
    original_save_response = _imf_save_response
    original_use_cache = _imf_use_cache
    original_wait_time = os.environ.get("IMF_WAIT_TIME", None)

    monkeypatch.setattr("imfp.utils._imf_save_response", False)
    monkeypatch.setattr("imfp.utils._imf_use_cache", False)
    set_imf_wait_time(0)

    yield

    monkeypatch.setattr("imfp.utils._imf_save_response", original_save_response)
    monkeypatch.setattr("imfp.utils._imf_use_cache", original_use_cache)
    if original_wait_time is not None:
        os.environ["IMF_WAIT_TIME"] = original_wait_time
    else:
        os.environ.pop("IMF_WAIT_TIME", None)


# ---------------------------------------------------------------------------
# Step 1: imf_get_dataflows
# ---------------------------------------------------------------------------


def test_imf_get_dataflows(set_options, use_saved_responses):
    result = imf_get_dataflows()

    assert isinstance(result, pd.DataFrame)
    assert list(result.columns) == [
        "id",
        "name",
        "description",
        "version",
        "agency",
        "structure",
        "last_updated",
    ]
    assert len(result) > 0
    assert result["id"].notna().all()
    assert not result["id"].duplicated().any()

    # A known dataflow, with the metadata columns populated.
    gfs = result[result["id"] == "GFS_SOO"]
    assert len(gfs) == 1
    assert gfs.iloc[0]["agency"] == "IMF.STA"
    assert gfs.iloc[0]["structure"].startswith("urn:sdmx:")
    assert gfs.iloc[0]["last_updated"] is not None


# ---------------------------------------------------------------------------
# Step 2: imf_get_datastructure
# ---------------------------------------------------------------------------


def test_imf_get_datastructure(set_options, use_saved_responses):
    result = imf_get_datastructure("GFS_SOO")

    assert list(result.columns) == ["dimension_id", "type", "position"]
    assert (result["type"] == "Dimension").all()

    # Positions define the series key, so they must be complete and ordered.
    assert result["position"].notna().all()
    assert list(result["position"]) == sorted(result["position"])

    assert "COUNTRY" in set(result["dimension_id"])
    # GFS_SOO spells frequency out in full; the package must not assume "FREQ".
    assert "FREQUENCY" in set(result["dimension_id"])


def test_imf_get_datastructure_include_time_and_measures(
    set_options, use_saved_responses
):
    base = imf_get_datastructure("GFS_SOO")
    full = imf_get_datastructure("GFS_SOO", include_time=True, include_measures=True)

    assert len(full) > len(base)
    assert "TIME_PERIOD" in set(full["dimension_id"])
    assert "OBS_VALUE" in set(full["dimension_id"])

    types = dict(zip(full["dimension_id"], full["type"]))
    assert types["TIME_PERIOD"] == "TimeDimension"
    assert types["OBS_VALUE"] == "Measure"

    # Measures occupy no slot in the series key.
    positions = dict(zip(full["dimension_id"], full["position"]))
    assert pd.isna(positions["OBS_VALUE"])


def test_imf_get_datastructure_rejects_unknown_dataflow(
    set_options, use_saved_responses
):
    with pytest.raises(ValueError):
        imf_get_datastructure("not_a_real_dataflow", max_tries=1)


# ---------------------------------------------------------------------------
# Step 3: imf_get_codelists
# ---------------------------------------------------------------------------


def test_imf_get_codelists(set_options, use_saved_responses):
    result = imf_get_codelists("COUNTRY", "GFS_SOO")

    assert list(result.columns) == [
        "dimension_id",
        "code",
        "name",
        "description",
        "codelist_id",
        "codelist_agency",
        "codelist_version",
    ]
    assert len(result) > 100
    assert (result["dimension_id"] == "COUNTRY").all()
    assert result["code"].notna().all()
    assert result["codelist_id"].notna().all()
    assert result["codelist_agency"].notna().all()
    assert result["codelist_version"].notna().all()

    # GFS_SOO country codes are ISO3, not the numeric IMF codes.
    codes = set(result["code"])
    assert {"AFG", "ALB", "DZA"}.issubset(codes)
    assert not any(code.isdigit() for code in codes)


def test_imf_get_codelists_accepts_multiple_dimensions(
    set_options, use_saved_responses
):
    result = imf_get_codelists(["COUNTRY", "FREQUENCY"], "GFS_SOO")

    by_dimension = result.groupby("dimension_id").size()
    assert set(by_dimension.index) == {"COUNTRY", "FREQUENCY"}
    assert by_dimension["COUNTRY"] > 100

    frequencies = set(result[result["dimension_id"] == "FREQUENCY"]["code"])
    assert {"A", "Q"}.issubset(frequencies)


def test_imf_get_codelists_is_case_insensitive(set_options, use_saved_responses):
    lower = imf_get_codelists("country", "GFS_SOO")
    upper = imf_get_codelists("COUNTRY", "GFS_SOO")

    # Requested case does not leak into the output.
    assert (lower["dimension_id"] == "COUNTRY").all()
    assert lower.equals(upper)


def test_imf_get_codelists_rejects_unknown_dimension(set_options, use_saved_responses):
    with pytest.raises(ValueError) as excinfo:
        imf_get_codelists("NOT_A_DIMENSION", "GFS_SOO")

    message = str(excinfo.value)
    assert "NOT_A_DIMENSION" in message
    # The error should point at the fix, not just the failure.
    assert "COUNTRY" in message
    assert "imf_get_datastructure" in message


def test_imf_get_codelists_requires_a_dimension(set_options, use_saved_responses):
    with pytest.raises(ValueError):
        imf_get_codelists([], "GFS_SOO")


# ---------------------------------------------------------------------------
# Step 4: imf_get
# ---------------------------------------------------------------------------

GFS_SOO_QUERY = {
    "COUNTRY": "ABW",
    "SECTOR": "S13",
    "GFS_GRP": "G2M",
    "INDICATOR": ["G23_T"],
    "TYPE_OF_TRANSFORMATION": "POGDP_PT",
    "FREQUENCY": "A",
}


def test_imf_get(set_options, use_saved_responses):
    result = imf_get(
        "GFS_SOO",
        dimensions=GFS_SOO_QUERY,
        start_period=1972,
        end_period=1976,
    )

    assert isinstance(result, pd.DataFrame)
    assert len(result) > 0
    # Dimension columns keep their SDMX IDs, then TIME_PERIOD and OBS_VALUE.
    assert list(result.columns) == [
        "COUNTRY",
        "SECTOR",
        "GFS_GRP",
        "INDICATOR",
        "TYPE_OF_TRANSFORMATION",
        "FREQUENCY",
        "TIME_PERIOD",
        "OBS_VALUE",
    ]
    assert set(result["COUNTRY"]) == {"ABW"}
    assert set(result["INDICATOR"]) == {"G23_T"}


def test_imf_get_kwargs_match_dimensions_dict(set_options, use_saved_responses):
    from_dict = imf_get(
        "GFS_SOO", dimensions=GFS_SOO_QUERY, start_period=1972, end_period=1976
    )
    from_kwargs = imf_get(
        "GFS_SOO",
        country="ABW",
        sector="S13",
        gfs_grp="G2M",
        indicator=["G23_T"],
        type_of_transformation="POGDP_PT",
        frequency="A",
        start_period="1972",
        end_period="1976",
    )

    assert from_dict.equals(from_kwargs)


def test_imf_get_parses_numeric_observations(set_options, use_saved_responses):
    result = imf_get(
        "AFRREO", indicator=["TTT_IX", "GGX_G01_GDP_PT"], start_period=2021
    )

    assert len(result) > 1
    assert result["OBS_VALUE"].dtype == "float64"
    assert set(result["INDICATOR"]).issubset({"TTT_IX", "GGX_G01_GDP_PT"})
    assert "TIME_PERIOD" in result.columns


def test_imf_get_matches_legacy_imf_dataset(set_options, use_saved_responses):
    """The new path must produce the same data as the function it replaces."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        legacy = imf_dataset(
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

    new = imf_get(
        "GFS_SOO", dimensions=GFS_SOO_QUERY, start_period=1972, end_period=1976
    )

    # imf_dataset lower-cases its columns; imf_get keeps the SDMX IDs.
    legacy.columns = [column.upper() for column in legacy.columns]
    assert legacy.equals(new)


def test_imf_get_rejects_unknown_dimension(set_options, use_saved_responses):
    with pytest.raises(ValueError) as excinfo:
        imf_get("GFS_SOO", not_a_dimension="X")

    message = str(excinfo.value)
    assert "NOT_A_DIMENSION" in message
    assert "COUNTRY" in message


def test_imf_get_rejects_duplicate_dimension(set_options, use_saved_responses):
    with pytest.raises(ValueError) as excinfo:
        imf_get("GFS_SOO", dimensions={"COUNTRY": "ABW"}, country="ABW")

    assert "more than once" in str(excinfo.value)


def test_imf_get_rejects_dataframe_codes(set_options, use_saved_responses):
    """imf_parameters passed DataFrames around; imf_get takes plain codes."""
    codes = imf_get_codelists("COUNTRY", "GFS_SOO")

    with pytest.raises(ValueError) as excinfo:
        imf_get("GFS_SOO", country=codes)

    assert "imf_get_codelists" in str(excinfo.value)


def test_imf_get_rejects_non_string_codes(set_options, use_saved_responses):
    with pytest.raises(ValueError):
        imf_get("GFS_SOO", country=[123])


def test_imf_get_rejects_malformed_periods(set_options, use_saved_responses):
    # A list is caught by the signature's type enforcement.
    with pytest.raises(TypeError):
        imf_get("GFS_SOO", country="ABW", start_period=[1999, 2004])

    with pytest.raises(ValueError):
        imf_get("GFS_SOO", country="ABW", end_period="   ")


def test_imf_get_warns_on_empty_result(set_options, monkeypatch):
    """An empty response is a warning plus an empty frame, not an exception."""

    def fake_download_parse(path, times=3, query_params=None, **kwargs):
        return {"data": {"dataSets": [{"series": {}}], "structures": [{}]}}

    monkeypatch.setattr("imfp.api._download_parse", fake_download_parse)
    monkeypatch.setattr(
        "imfp.api._build_data_request",
        lambda *args, **kwargs: ("data/dataflow/IMF.STA/GFS_SOO/+/ABW", {}),
    )

    with pytest.warns(UserWarning, match="No observations matched"):
        result = imf_get("GFS_SOO", country="ABW")

    assert isinstance(result, pd.DataFrame)
    assert result.empty


def test_imf_get_return_raw(set_options, use_saved_responses):
    raw = imf_get(
        "GFS_SOO",
        dimensions=GFS_SOO_QUERY,
        start_period=1972,
        end_period=1976,
        return_raw=True,
    )

    assert isinstance(raw, dict)
    assert "data" in raw


# ---------------------------------------------------------------------------
# Deprecation of the pre-2.0 API
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "call, replacement",
    [
        (lambda: imf_databases(), "imf_get_dataflows"),
        (lambda: imf_parameters("GFS_SOO"), "imf_get_codelists"),
        (lambda: imf_parameter_defs("BOP"), "imf_get_datastructure"),
    ],
)
def test_legacy_functions_warn(set_options, use_saved_responses, call, replacement):
    with pytest.warns(DeprecationWarning) as record:
        call()

    messages = [str(w.message) for w in record]
    assert any(replacement in message for message in messages)
    assert any("3.0.0" in message for message in messages)


def test_legacy_imf_dataset_warns(set_options, use_saved_responses):
    with pytest.warns(DeprecationWarning) as record:
        imf_dataset(
            database_id="AFRREO",
            indicator=["TTT_IX", "GGX_G01_GDP_PT"],
            start_year=2021,
        )

    assert any("imf_get" in str(w.message) for w in record)
