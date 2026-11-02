"""Tests for the category, dispatchable, non-dispatchable and total data frames"""

import pandas as pd
import pytest

from generation import (Coal, NaturalGas, Hydro, Solar, Wind,
    Dispatchable, Nondispatchable, Total)
from generation.category import Category, clear
from generation.cli import main, E_OK
from generation.fuels import CATEGORIES, DISPATCHABLE, NONDISPATCHABLE, category

from conftest import FakeForm923, FakeForm930Fuel

DISPATCHABLE_COLUMNS = [f"{x}_MW" for x in DISPATCHABLE] + ["dispatchable_MW"]
NONDISPATCHABLE_COLUMNS = ["solar_MW", "wind_MW", "nondispatchable_MW"]


@pytest.mark.parametrize("fuel,pm,expected", [
    ("SUB", "ST", "coal"),
    ("NG", "CT", "natural_gas"),
    ("DFO", "IC", "oil"),
    ("NUC", "ST", "nuclear"),
    ("WAT", "HY", "hydro"),
    ("WAT", "PS", "pumped_storage"),
    ("MWH", "BA", "battery_storage"),
    ("GEO", "BT", "geothermal"),
    ("WDS", "ST", "biomass"),
    ("SUN", "PV", "solar"),
    ("WND", "WT", "wind"),
    ("WH", "OT", "other"),
    (None, None, "other"),
])
def test_fuel_category(fuel, pm, expected):
    assert category(fuel, pm) == expected


def test_categories_split():
    assert sorted(DISPATCHABLE + NONDISPATCHABLE) == sorted(CATEGORIES)
    assert len(CATEGORIES) == 12


def test_category_frame():
    data = Hydro("CA", "Stanislaus", 2020)
    assert list(data.columns) == ["plant_151_MW", "hydro_MW"]
    assert len(data) == 8784
    assert data.index.name == "timestamp"
    assert str(data.index.tz) == "UTC"
    assert data.index[0] == pd.Timestamp("2020-01-01", tz="UTC")
    assert data["hydro_MW"].equals(data["plant_151_MW"])


def test_monthly_energy_matches_form923():
    data = Solar("CA", "Stanislaus", 2020)
    monthly = data["solar_MW"].groupby(data.index.month).sum()
    hours = pd.Series(data.index.month).value_counts().sort_index()
    assert monthly.round(3).tolist() == (5.0 * hours).round(3).tolist()


def test_shaped_by_form930():
    data = Solar("CA", "Stanislaus", 2020)
    assert data.loc[data.index.hour == 8, "solar_MW"].max() == 0
    assert data.loc[data.index.hour == 20, "solar_MW"].min() > 0


def test_flat_when_no_form930():
    with pytest.warns(UserWarning):
        data = NaturalGas("CA", "Placer", 2020)
    assert list(data.columns) == ["plant_34_MW", "natural_gas_MW"]
    assert (data["natural_gas_MW"] == 10.0).all()


def test_increments_excluded():
    assert all(not x[3] for x in FakeForm923.calls) or not FakeForm923.calls
    NaturalGas("CA", "Stanislaus", 2020)
    assert FakeForm923.calls[-1][3] is False


def test_empty_category():
    data = Coal("CA", "Stanislaus", 2020)
    assert list(data.columns) == ["coal_MW"]
    assert (data["coal_MW"] == 0).all()


def test_cached():
    first = Hydro("CA", "Stanislaus", 2020)
    clear()
    FakeForm923.calls = []
    second = Hydro("CA", "Stanislaus", 2020)
    assert FakeForm923.calls == []
    pd.testing.assert_frame_equal(pd.DataFrame(first), pd.DataFrame(second), check_freq=False)


def test_refresh():
    Hydro("CA", "Stanislaus", 2020)
    clear()
    FakeForm923.calls = []
    Hydro("CA", "Stanislaus", 2020, refresh=True)
    assert len(FakeForm923.calls) == 1


@pytest.mark.parametrize("args,error", [
    (("California", "Kern", 2020), ValueError),
    (("CA", "", 2020), ValueError),
    (("CA", "Kern", 2017), ValueError),
    (("CA", "Kern", "2020"), TypeError),
])
def test_invalid_arguments(args, error):
    with pytest.raises(error):
        Wind(*args)


def test_base_class_not_constructible():
    with pytest.raises(AssertionError):
        Category("CA", "Stanislaus", 2020)


def test_unknown_county():
    with pytest.warns(UserWarning):
        data = Total("CA", "Kern", 2020)
    assert (data["total_MW"] == 0).all()


def test_dispatchable():
    data = Dispatchable("CA", "Stanislaus", 2020)
    assert list(data.columns) == DISPATCHABLE_COLUMNS
    assert (data["dispatchable_MW"] - data[DISPATCHABLE_COLUMNS[:-1]].sum(axis=1)).abs().max() < 1e-6
    assert (data["hydro_MW"] == 30.0).all()


def test_nondispatchable():
    data = Nondispatchable("CA", "Stanislaus", 2020)
    assert list(data.columns) == NONDISPATCHABLE_COLUMNS
    assert (data["nondispatchable_MW"] - data["solar_MW"] - data["wind_MW"]).abs().max() < 1e-6


def test_total():
    data = Total("CA", "Stanislaus", 2020)
    assert list(data.columns) == DISPATCHABLE_COLUMNS + NONDISPATCHABLE_COLUMNS + ["total_MW"]
    assert (data["total_MW"] - data["dispatchable_MW"] - data["nondispatchable_MW"]).abs().max() < 1e-6
    assert abs(data["total_MW"].mean() - 35.0) < 1e-3


def test_form930_loaded_once_per_ba():
    Total("CA", "Stanislaus", 2020)
    assert FakeForm930Fuel.calls == [("BANC", 2020)]


def test_makeargs():
    assert Total.makeargs(state="CA", county="Kern", year=2020, output="x") == \
        {"state": "CA", "county": "Kern", "year": 2020}


def test_cli_total(tmp_path):
    out = tmp_path / "total.csv"
    assert main("2020", "CA", "-C", "Stanislaus", "-D", "total", "-o", str(out)) == E_OK
    lines = out.read_text().splitlines()
    assert lines[0].startswith("timestamp,coal_MW,")
    assert lines[0].endswith(",total_MW")
    assert len(lines) == 8785


def test_cli_category_month(tmp_path):
    out = tmp_path / "hydro.csv"
    assert main("2020", "8", "CA", "-C", "Stanislaus", "-D", "hydro", "-o", str(out)) == E_OK
    assert len(out.read_text().splitlines()) == 31 * 24 + 1


def test_cli_hourly_requires_county():
    assert main("2020", "CA", "-D", "total") != E_OK
