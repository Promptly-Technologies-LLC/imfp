"""Regression tests for imf_dataset subprocesses.

These guard correctness and performance of the pieces that issue #68 will
simplify/modularize (parameter coercion/filtering, series-key construction,
period transforms, SDMX JSON parsing, and request orchestration).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pandas as pd
import pytest
import responses

from imfp import imf_dataset, imf_parameters, set_imf_wait_time
from imfp.data import (
    _normalize_year_arg,
    _parse_imf_sdmx_json,
    _transform_period_for_frequency,
)
from imfp.utils import _imf_save_response, _imf_use_cache

wait_time = 0


@pytest.fixture
def set_options(monkeypatch):
    os.makedirs("tests/responses", exist_ok=True)
    original_save_response = _imf_save_response
    original_use_cache = _imf_use_cache
    original_wait_time = os.environ.get("IMF_WAIT_TIME", None)

    monkeypatch.setattr("imfp.utils._imf_save_response", False)
    monkeypatch.setattr("imfp.utils._imf_use_cache", False)
    set_imf_wait_time(wait_time)

    yield

    monkeypatch.setattr("imfp.utils._imf_save_response", original_save_response)
    monkeypatch.setattr("imfp.utils._imf_use_cache", original_use_cache)
    if original_wait_time is not None:
        os.environ["IMF_WAIT_TIME"] = original_wait_time
    else:
        os.environ.pop("IMF_WAIT_TIME", None)


def _synthetic_sdmx_message(
    *,
    series: dict | None = None,
    series_dims: list[dict] | None = None,
    obs_dim_values: list[dict] | None = None,
    include_data: bool = True,
    include_datasets: bool = True,
    include_structures: bool = True,
) -> dict:
    """Build a minimal SDMX 3.0 JSON message for parser unit tests."""
    if series_dims is None:
        series_dims = [
            {
                "id": "COUNTRY",
                "values": [{"id": "US"}, {"id": "CA"}],
            },
            {
                "id": "INDICATOR",
                "values": [{"id": "NGDP_RPCH"}],
            },
            {
                "id": "FREQUENCY",
                "values": [{"id": "A"}],
            },
        ]
    if obs_dim_values is None:
        obs_dim_values = [{"value": "2020"}, {"value": "2021"}, {"value": "2022"}]
    if series is None:
        series = {
            "0:0:0": {
                "observations": {
                    "0": ["1.5"],
                    "1": ["NA"],
                    "2": ["2.25"],
                }
            },
            "1:0:0": {
                "observations": {
                    "0": ["3.0"],
                    "1": ["NP"],
                }
            },
        }

    message: dict = {}
    if not include_data:
        return message

    data: dict = {}
    if include_datasets:
        data["dataSets"] = [{"series": series}]
    if include_structures:
        data["structures"] = [
            {
                "dimensions": {
                    "series": series_dims,
                    "observation": [{"id": "TIME_PERIOD", "values": obs_dim_values}],
                }
            }
        ]
    message["data"] = data
    return message


def _capture_requests():
    """Return a responses mock that replays cached fixtures and records URLs."""
    urls: list[str] = []

    def responder(request):
        urls.append(request.url)
        file_name = hashlib.sha256(request.url.encode()).hexdigest()
        file_path = Path("tests/responses") / f"{file_name}.json"
        if not file_path.exists():
            raise AssertionError(
                f"No cached HTTP fixture for URL: {request.url}\n"
                f"Expected file: {file_path}"
            )
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        status = int(data.get("status_code", 200))
        body = data.get("text") or data.get("content") or ""
        headers = dict(data.get("headers", {}))
        for key in (
            "content-encoding",
            "Content-Encoding",
            "content-length",
            "Content-Length",
        ):
            headers.pop(key, None)
        return (status, headers, body)

    rsps = responses.RequestsMock(assert_all_requests_are_fired=False)
    rsps.start()
    rsps.add_callback(responses.GET, re.compile(r".*"), callback=responder)
    return rsps, urls


def _data_request_urls(urls: list[str]) -> list[str]:
    return [u for u in urls if "/data/dataflow/" in u]


# ---------------------------------------------------------------------------
# SDMX JSON parsing (_parse_imf_sdmx_json)
# ---------------------------------------------------------------------------


def test_parse_imf_sdmx_json_empty_and_missing_sections():
    assert _parse_imf_sdmx_json({}).empty
    assert _parse_imf_sdmx_json({"data": {}}).empty
    assert _parse_imf_sdmx_json(_synthetic_sdmx_message(include_datasets=False)).empty
    assert _parse_imf_sdmx_json(_synthetic_sdmx_message(include_structures=False)).empty
    assert _parse_imf_sdmx_json(
        _synthetic_sdmx_message(series={})
    ).empty  # no series keys


def test_parse_imf_sdmx_json_decodes_series_and_observations():
    df = _parse_imf_sdmx_json(_synthetic_sdmx_message())

    assert list(df.columns) == [
        "COUNTRY",
        "INDICATOR",
        "FREQUENCY",
        "TIME_PERIOD",
        "OBS_VALUE",
    ]
    assert len(df) == 5
    assert set(df["COUNTRY"]) == {"US", "CA"}
    assert set(df["INDICATOR"]) == {"NGDP_RPCH"}
    assert set(df["FREQUENCY"]) == {"A"}

    us = df[df["COUNTRY"] == "US"].sort_values("TIME_PERIOD")
    assert us["TIME_PERIOD"].tolist() == ["2020", "2021", "2022"]
    assert us["OBS_VALUE"].tolist()[0] == pytest.approx(1.5)
    assert pd.isna(us["OBS_VALUE"].tolist()[1])  # "NA" -> None
    assert us["OBS_VALUE"].tolist()[2] == pytest.approx(2.25)

    ca = df[df["COUNTRY"] == "CA"]
    assert pd.isna(ca.loc[ca["TIME_PERIOD"] == "2021", "OBS_VALUE"].iloc[0])  # "NP"


def test_parse_imf_sdmx_json_skips_series_without_observations():
    message = _synthetic_sdmx_message(
        series={
            "0:0:0": {"observations": {}},
            "1:0:0": {"observations": {"0": ["4.0"]}},
        }
    )
    df = _parse_imf_sdmx_json(message)
    assert len(df) == 1
    assert df.iloc[0]["COUNTRY"] == "CA"
    assert df.iloc[0]["OBS_VALUE"] == pytest.approx(4.0)


def test_parse_imf_sdmx_json_maps_common_missing_value_flags():
    message = _synthetic_sdmx_message(
        series={
            "0:0:0": {
                "observations": {
                    "0": ["ND"],
                    "1": ["N/A"],
                    "2": ["not-a-number"],
                }
            }
        }
    )
    df = _parse_imf_sdmx_json(message)
    # ND and N/A map to None; other non-numeric strings also become None via float() fail
    assert df["OBS_VALUE"].isna().all()


def test_parse_imf_sdmx_json_performance_large_message():
    """Parsing should stay linear-ish: large synthetic payload finishes quickly."""
    n_series = 200
    n_obs = 120
    series_dims = [
        {"id": "COUNTRY", "values": [{"id": f"C{i:03d}"} for i in range(n_series)]},
        {"id": "INDICATOR", "values": [{"id": "X"}]},
        {"id": "FREQUENCY", "values": [{"id": "A"}]},
    ]
    obs_values = [{"value": str(2000 + i)} for i in range(n_obs)]
    series = {
        f"{i}:0:0": {
            "observations": {str(j): [str(float(i + j))] for j in range(n_obs)}
        }
        for i in range(n_series)
    }
    message = _synthetic_sdmx_message(
        series=series, series_dims=series_dims, obs_dim_values=obs_values
    )

    # Warm once so import/pandas setup is not charged against the budget.
    _parse_imf_sdmx_json(message)

    start = time.perf_counter()
    df = _parse_imf_sdmx_json(message)
    elapsed = time.perf_counter() - start

    assert len(df) == n_series * n_obs
    # Generous ceiling: current implementation is well under this on CI/dev CPUs.
    # The goal is to catch pathological regressions (e.g. accidental O(n^2) copies).
    assert elapsed < 2.0, f"parse took {elapsed:.3f}s for {len(df)} rows"


# ---------------------------------------------------------------------------
# Year / period helpers extracted from imf_dataset
# ---------------------------------------------------------------------------


def test_normalize_year_arg_accepts_int_and_str():
    assert _normalize_year_arg(None, "start_year") is None
    assert _normalize_year_arg(2010, "start_year") == "2010"
    assert _normalize_year_arg("2010", "end_year") == "2010"
    with pytest.raises(ValueError, match="start_year must be a four-digit"):
        _normalize_year_arg(10, "start_year")
    with pytest.raises(ValueError, match="end_year must be a four-digit"):
        _normalize_year_arg("abcd", "end_year")


def test_transform_period_for_frequency_variants():
    assert _transform_period_for_frequency(None, ["A"]) is None
    assert _transform_period_for_frequency("2019-M01", ["M"]) == "2019-M01"
    assert _transform_period_for_frequency("2019-01", ["M"]) == "2019-M01"
    assert _transform_period_for_frequency("2015", ["A"]) == "2015-A1"
    assert _transform_period_for_frequency("2015", ["Q"]) == "2015-Q1"
    assert _transform_period_for_frequency("2015", ["M"]) == "2015-M01"
    assert _transform_period_for_frequency("2015", None) == "2015-A1"
    assert _transform_period_for_frequency("2015", ["A", "Q"]) == "2015-A1"


# ---------------------------------------------------------------------------
# Parameter coercion, filtering, and request construction
# ---------------------------------------------------------------------------


def test_imf_dataset_parameters_dict_matches_kwargs(set_options):
    """parameters= and **kwargs filtering should produce identical series keys."""
    rsps, urls = _capture_requests()
    try:
        params = imf_parameters("GFS_SOO", times=1)
        for key in list(params):
            if key == "country":
                params[key] = params[key][params[key]["input_code"] == "ABW"]
            elif key == "sector":
                params[key] = params[key][params[key]["input_code"] == "S13"]
            elif key == "gfs_grp":
                params[key] = params[key][params[key]["input_code"] == "G2M"]
            elif key == "indicator":
                params[key] = params[key][params[key]["input_code"] == "G23_T"]
            elif key == "type_of_transformation":
                params[key] = params[key][params[key]["input_code"] == "POGDP_PT"]
            elif key in ("freq", "frequency"):
                params[key] = params[key][params[key]["input_code"] == "A"]
            else:
                params[key] = params[key].iloc[0:0]

        urls.clear()
        df_params = imf_dataset(
            database_id="GFS_SOO",
            parameters=params,
            start_year=1972,
            end_year=1976,
            times=1,
        )
        params_urls = list(_data_request_urls(urls))
        urls.clear()

        with pytest.warns(UserWarning, match="Coercing parameter 'freq'"):
            df_kwargs = imf_dataset(
                database_id="GFS_SOO",
                country="ABW",
                sector="S13",
                gfs_grp="G2M",
                indicator=["G23_T"],
                type_of_transformation="POGDP_PT",
                freq="A",
                start_year=1972,
                end_year=1976,
                times=1,
            )
        kwargs_urls = list(_data_request_urls(urls))
    finally:
        rsps.stop()
        rsps.reset()

    assert len(params_urls) == 1 and len(kwargs_urls) == 1
    assert params_urls[0] == kwargs_urls[0]
    pd.testing.assert_frame_equal(
        df_params.sort_values(list(df_params.columns)).reset_index(drop=True),
        df_kwargs.sort_values(list(df_kwargs.columns)).reset_index(drop=True),
    )


def test_imf_dataset_builds_series_key_and_time_filter_for_imf_sta(set_options):
    rsps, urls = _capture_requests()
    try:
        with pytest.warns(UserWarning, match="Coercing parameter 'freq'"):
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
                times=1,
            )
    finally:
        rsps.stop()
        rsps.reset()

    assert len(df) > 0
    data_urls = _data_request_urls(urls)
    assert len(data_urls) == 1
    parsed = urlparse(data_urls[0])
    # Path ends with .../GFS_SOO/+/ABW.S13.G2M.G23_T.POGDP_PT.A
    assert parsed.path.endswith("/GFS_SOO/+/ABW.S13.G2M.G23_T.POGDP_PT.A")
    qs = parse_qs(parsed.query)
    assert qs["dimensionAtObservation"] == ["TIME_PERIOD"]
    assert qs["attributes"] == ["dsd"]
    assert qs["measures"] == ["all"]
    assert qs["c[TIME_PERIOD]"] == ["ge:1972-A1+le:1976-A1"]


def test_imf_dataset_ignores_time_filters_for_non_sta_agency(set_options):
    rsps, urls = _capture_requests()
    try:
        with pytest.warns(UserWarning, match="does not support time filters"):
            imf_dataset(
                database_id="WHDREO",
                freq="A",
                country="GX1213",
                indicator=["BCA_GDP_BP6"],
                start_year=2010,
                end_year=2012,
                times=1,
            )
    finally:
        rsps.stop()
        rsps.reset()

    data_urls = _data_request_urls(urls)
    assert len(data_urls) == 1
    qs = parse_qs(urlparse(data_urls[0]).query)
    assert "c[TIME_PERIOD]" not in qs
    assert urlparse(data_urls[0]).path.endswith("/WHDREO/+/GX1213.BCA_GDP_BP6.A")


def test_imf_dataset_coerces_freq_alias(set_options):
    rsps, urls = _capture_requests()
    try:
        with pytest.warns(UserWarning, match="Coercing parameter 'freq'"):
            imf_dataset(
                database_id="WHDREO",
                freq="A",
                country="GX1213",
                indicator=["BCA_GDP_BP6"],
                times=1,
            )
    finally:
        rsps.stop()
        rsps.reset()

    data_urls = _data_request_urls(urls)
    assert urlparse(data_urls[0]).path.endswith("/GX1213.BCA_GDP_BP6.A")


def test_imf_dataset_return_raw_and_print_url(set_options, capsys):
    rsps, urls = _capture_requests()
    try:
        with pytest.warns(UserWarning, match="Coercing parameter 'freq'"):
            raw = imf_dataset(
                database_id="WHDREO",
                freq="A",
                country="GX1213",
                indicator=["BCA_GDP_BP6"],
                return_raw=True,
                print_url=True,
                times=1,
            )
        with pytest.warns(UserWarning, match="Coercing parameter 'freq'"):
            meta, raw_meta = imf_dataset(
                database_id="WHDREO",
                freq="A",
                country="GX1213",
                indicator=["BCA_GDP_BP6"],
                return_raw=True,
                include_metadata=True,
                times=1,
            )
    finally:
        rsps.stop()
        rsps.reset()

    assert isinstance(raw, dict)
    assert "data" in raw
    assert isinstance(meta, dict)
    assert isinstance(raw_meta, dict)

    printed = capsys.readouterr().out
    assert "data/dataflow/" in printed
    assert "WHDREO" in printed


def test_imf_dataset_year_validation_accepts_int_and_str(set_options):
    rsps, _ = _capture_requests()
    try:
        df_int = imf_dataset(
            database_id="GFS_SOO",
            country="ABW",
            sector="S13",
            gfs_grp="G2M",
            indicator=["G23_T"],
            type_of_transformation="POGDP_PT",
            freq="A",
            start_year=1972,
            end_year=1976,
            times=1,
        )
        df_str = imf_dataset(
            database_id="GFS_SOO",
            country="ABW",
            sector="S13",
            gfs_grp="G2M",
            indicator=["G23_T"],
            type_of_transformation="POGDP_PT",
            freq="A",
            start_year="1972",
            end_year="1976",
            times=1,
        )
    finally:
        rsps.stop()
        rsps.reset()

    pd.testing.assert_frame_equal(
        df_int.sort_values(list(df_int.columns)).reset_index(drop=True),
        df_str.sort_values(list(df_str.columns)).reset_index(drop=True),
    )


def test_imf_dataset_no_filters_warns_and_wildcards(set_options, capsys):
    # APDREO has a cached wildcard data fixture from error-handling tests.
    rsps, urls = _capture_requests()
    try:
        # May raise if no data for full DB; we only care about the user message
        # and that the series key is all wildcards when filters are omitted.
        try:
            imf_dataset(database_id="APDREO", times=1)
        except ValueError as exc:
            # Empty DB responses are acceptable for this path.
            assert "No data found" in str(exc) or "combination of parameters" in str(
                exc
            )
    finally:
        rsps.stop()
        rsps.reset()

    out = capsys.readouterr().out
    assert "User supplied no filter parameters" in out
    data_urls = _data_request_urls(urls)
    assert len(data_urls) == 1
    # All non-time dimensions wildcarded
    assert urlparse(data_urls[0]).path.endswith("/APDREO/+/*.*.*")


# ---------------------------------------------------------------------------
# Request-count / orchestration performance ceiling
# ---------------------------------------------------------------------------


def test_imf_dataset_request_count_ceiling(set_options):
    """Guard against request amplification when orchestration is refactored.

    Current WHDREO path issues duplicate dataflow lookups. Refactors may reduce
    this count; they must not increase it.
    """
    rsps, urls = _capture_requests()
    try:
        imf_dataset(
            database_id="WHDREO",
            freq="A",
            country="GX1213",
            indicator=["BCA_GDP_BP6"],
            start_year=2010,
            end_year=2012,
            times=1,
        )
    finally:
        rsps.stop()
        rsps.reset()

    # Baseline after sharing one dataflow lookup for DSD + agency resolution.
    # imf_parameters() still performs its own catalog/DSD fetches upstream.
    assert len(urls) <= 14
    dataflow_list_fetches = sum(
        1 for u in urls if "structure/dataflow/all/" in u and "/data/" not in u
    )
    assert dataflow_list_fetches <= 2
    assert len(_data_request_urls(urls)) == 1
