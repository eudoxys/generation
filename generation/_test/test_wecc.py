"""Tests of the WECC file builder `data/wecc/build_wecc.py` (offline fakes)"""

import os
import importlib.util

import pandas as pd
import pytest

from generation.fuels import CATEGORIES

from conftest import FakeForm923, hours

PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "wecc", "build_wecc.py")


@pytest.fixture
def wecc(monkeypatch):
    """Load the builder with the fake Form 923"""
    spec = importlib.util.spec_from_file_location("build_wecc", PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "Form923", FakeForm923)
    return module


def test_files(wecc, tmp_path):
    files = wecc.build(2020, 2021, str(tmp_path))
    assert sorted(files) == sorted(f"{x}_{y}" for x in ("capacity", "actual") for y in CATEGORIES)
    for pathname in files.values():
        assert os.path.basename(pathname).endswith(".csv.gz")
        data = pd.read_csv(pathname, index_col=0)
        assert len(data) == len(hours(2020)) + len(hours(2021))
        assert list(data.columns) == ["Placer CA", "Stanislaus CA", "King WA"]
        assert data.index[0] == "2020-01-01 00:00:00+00:00"
        assert data.index[-1] == "2021-12-31 23:00:00+00:00"


def test_capacity(wecc, tmp_path):
    files = wecc.build(2020, 2020, str(tmp_path))
    hydro = pd.read_csv(files["capacity_hydro"], index_col=0)
    assert (hydro["Stanislaus CA"] == 53.5).all()
    assert (hydro["King WA"] == 100.0).all()
    assert (hydro["Placer CA"] == 0).all()
    gas = pd.read_csv(files["capacity_natural_gas"], index_col=0)
    assert (gas["Placer CA"] == 12.1).all()


def test_actual(wecc, tmp_path):
    files = wecc.build(2020, 2020, str(tmp_path))
    hydro = pd.read_csv(files["actual_hydro"], index_col=0)
    assert hydro["Stanislaus CA"].mean() == pytest.approx(30.0, abs=1e-3)
    assert hydro["King WA"].mean() == pytest.approx(80.0, abs=1e-3)
    solar = pd.read_csv(files["actual_solar"], index_col=0)
    assert solar["Stanislaus CA"].sum() == pytest.approx(5.0 * len(hours(2020)), rel=1e-6)
    assert solar["Stanislaus CA"].min() == 0  # shaped by the BANC diurnal profile
    assert (pd.read_csv(files["actual_coal"], index_col=0) == 0).all().all()


def test_wecc_filter(wecc, monkeypatch):
    import generation.fleet
    from conftest import ROWS
    rows = dict(ROWS)
    rows["ba"] = ["CISO", "SWPP", "BANC", ""]  # SPP plant out, WA plant with no BA in
    monkeypatch.setattr("conftest.ROWS", rows)
    fleet = wecc.plants(2020, [1])
    assert sorted(fleet["plant"].unique()) == [34, 152, 900]
