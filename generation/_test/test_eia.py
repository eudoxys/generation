"""Integration tests: the real `eia` classes with mocked EIA downloads

The other tests replace `eia.Form860m`, `eia.Form923` and `eia.Form930Fuel`
with the fakes in `conftest.py`. These tests run the real `eia` classes on
the synthetic EIA source files in `eia_samples.py` (served through a mocked
`requests.get`, so nothing is downloaded) and check that

  - the fakes return the same index, columns and values as the real
    classes, and

  - `Fleet` and the hourly frames are the same whether built from the fakes
    or from the real classes,

so a change to the `eia` API or output schema fails here instead of passing
silently against out-of-date fakes. Skipped when `eia` isn't installed.
"""

import os
from unittest import mock

import pandas as pd
import pytest

from cache import Cache

import generation.category
import generation.fleet
from generation import Fleet, Hydro, Solar, NaturalGas, Total

import eia_samples
from conftest import FakeForm860m, FakeForm923, FakeForm930Fuel

# pylint: disable=redefined-outer-name,unused-argument

pytest.importorskip("eia.base")  # skipped when conftest stubs eia
import eia  # noqa: E402 pylint: disable=wrong-import-position
import eia.base  # noqa: E402 pylint: disable=wrong-import-position
from eia.form930 import _Form930Base  # noqa: E402 pylint: disable=wrong-import-position

YEAR = 2020
BAS = ["BANC", "BPAT", "CISO"]


@pytest.fixture
def downloads(monkeypatch, tmp_path):
    """Serve the sample EIA files to the real `eia` classes

    Returns the list of URLs requested. Unknown URLs fail the test.
    """
    old = eia.base.set_cache_dir(str(tmp_path / "eia"))
    monkeypatch.setattr(_Form930Base, "references", {})
    monkeypatch.setattr(_Form930Base, "_references_refreshed", False)
    monkeypatch.setattr(_Form930Base, "_bulk", {})
    monkeypatch.setattr(_Form930Base, "_bulk_refreshed", set())
    monkeypatch.setenv("EIA_API_KEY", "TEST")
    months = {x.lower(): n for n, x in enumerate(pd.date_range("2000-01", periods=12,
        freq="MS").strftime("%B"), start=1)}
    urls = []

    def get(url, params=None, timeout=None):
        urls.append(url)
        name = url.rsplit("/", 1)[-1]
        params = dict(params or [])
        json = None
        if "/eia860m/" in url:
            month, year = name.removesuffix(".xlsx").split("_generator")
            content = eia_samples.form860m_workbook(int(year), months[month])
        elif "/eia923/" in url:
            content = eia_samples.form923_zip(int(name[5:9]))
        elif name == "EIA930_Reference_Tables.xlsx":
            content = eia_samples.form930_reference(*BAS)
        elif url.endswith("/rto/fuel-type-data/data/"):
            start = pd.Timestamp(params["start"])
            data = eia_samples.form930_fuel_records(start.year, start.month,
                params["facets[respondent][]"])
            data = data[params["offset"]:params["offset"] + params["length"]]
            content = b""
            json = {"response": {"total": str(len(data)), "data": data}}
        else:
            raise AssertionError(f"unexpected download {url}")
        response = mock.Mock(status_code=200, content=content)
        response.json.return_value = json
        return response

    monkeypatch.setattr(eia.base.requests, "get", get)
    yield urls
    eia.base.set_cache_dir(old)


@pytest.fixture
def real_eia(monkeypatch, downloads, tmp_path):
    """Use the real `eia` classes in `generation` (with a separate cache)"""
    monkeypatch.setattr(generation.fleet, "Form860m", eia.Form860m)
    monkeypatch.setattr(generation.category, "Form923", eia.Form923)
    monkeypatch.setattr(generation.category, "Form930Fuel", eia.Form930Fuel)
    monkeypatch.setattr(Cache, "CACHEDIR", str(tmp_path / "real"))
    generation.category.clear()
    return downloads


def assert_same_schema(fake, real):
    """Check that a fake frame has the index, columns and values of the real one"""
    assert list(fake.index.names) == list(real.index.names)
    missing = [x for x in fake.columns if x not in real.columns]
    assert not missing, f"fake columns {missing} not returned by eia"
    real = real[list(fake.columns)]
    assert fake.index.equals(real.index)
    for column in fake.columns:
        assert fake[column].dtype.kind == real[column].dtype.kind, column
    pd.testing.assert_frame_equal(pd.DataFrame(fake), pd.DataFrame(real),
        check_dtype=False, check_index_type=False)


def test_fake_form860m_matches_eia(downloads):
    real = eia.Form860m(YEAR, 8, subset="Operating")
    fake = FakeForm860m(YEAR, 8, subset="Operating")
    fake = fake.drop(columns=["unit"])  # blank in the workbook, read as NaN
    assert_same_schema(fake.sort_index(), real)
    assert any("august_generator2020" in x for x in downloads)


def test_fake_form923_matches_eia(downloads):
    for increments in (True, False):
        real = eia.Form923(YEAR, states=["CA"], by="plant", increments=increments)
        fake = FakeForm923(YEAR, states=["CA"], by="plant", increments=increments)
        assert list(fake.columns) == list(real.columns)
        assert_same_schema(fake.sort_index(), real.sort_index())


def test_fake_form930fuel_matches_eia(downloads):
    real = eia.Form930Fuel(YEAR, respondent="BANC")
    fake = FakeForm930Fuel(YEAR, respondent="BANC")
    assert list(fake.columns) == list(real.columns)
    assert str(real.index.tz) == "UTC"
    assert_same_schema(fake, real)


def test_form930fuel_invalid_respondent(downloads):
    with pytest.raises(ValueError):
        eia.Form930Fuel(YEAR, respondent="XXXX")
    with pytest.raises(ValueError):
        FakeForm930Fuel(YEAR, respondent="XXXX")


def build(request, cls, *args, **kwargs):
    """Build a frame with the fakes, then with the real `eia` classes"""
    fake = cls(*args, **kwargs)
    request.getfixturevalue("real_eia")
    return fake, cls(*args, **kwargs)


def test_fleet_with_eia(request):
    fake, real = build(request, Fleet, "CA", "Stanislaus", YEAR, months=[1, 8, 12])
    assert len(real) == 6
    pd.testing.assert_frame_equal(fake, real, check_dtype=False)


@pytest.mark.parametrize("cls", [Hydro, Solar, NaturalGas])
def test_category_with_eia(request, cls):
    fake, real = build(request, cls, "CA", "Stanislaus", YEAR)
    pd.testing.assert_frame_equal(fake, real)


def test_total_with_eia(request):
    fake, real = build(request, Total, "CA", "Placer", YEAR)
    assert real["natural_gas_MW"].sum() > 0
    pd.testing.assert_frame_equal(fake, real)


if __name__ == "__main__":
    pytest.main([os.path.abspath(__file__), "-v"])
