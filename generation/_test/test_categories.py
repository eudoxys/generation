"""Tests for the category, dispatchable, non-dispatchable and total data frames"""

import warnings

import numpy as np
import pandas as pd
import pytest

from generation import (Coal, NaturalGas, Hydro, Solar, Wind,
    Dispatchable, Nondispatchable, Total)
import generation.category as gc
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


def test_shape_follows_form930():
    shape = gc._shape("BANC", 2020, 1, "SUN")
    assert abs(shape.sum() - 1) < 1e-9
    assert shape.idxmax().hour == 20
    assert not shape.eq(shape.iloc[0]).all()


def test_form930_api_errors_not_hidden(monkeypatch):

    def broken(*args, **kwargs):
        raise TypeError("unexpected argument")

    monkeypatch.setattr(gc, "Form930Fuel", broken)
    with pytest.raises(TypeError):
        gc._shape("BANC", 2020, 1, "SUN")


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
    assert FakeForm930Fuel.calls == [("BANC", 2020, x) for x in range(1, 13)]


def test_form930_failed_month_is_flat_only_that_month():
    FakeForm930Fuel.failures = {("BANC", 2020, 3)}
    with pytest.warns(UserWarning, match="BANC in 2020 month.s. 03"):
        data = Solar("CA", "Stanislaus", 2020)
    march = data.loc[data.index.month == 3, "solar_MW"]
    april = data.loc[data.index.month == 4, "solar_MW"]
    assert march.nunique() == 1
    assert april.nunique() > 1
    assert march.sum() == pytest.approx(5.0 * len(march), rel=1e-6)


def test_form930_failed_download_retried(monkeypatch):
    calls = []

    class Flaky(FakeForm930Fuel):
        def __init__(self, year, month=None, *, respondent, refresh=False, **kwargs):
            calls.append((month, refresh))
            if month == 5 and not refresh:
                raise RuntimeError("download failed")
            super().__init__(year, month, respondent=respondent, refresh=refresh, **kwargs)

    monkeypatch.setattr(gc, "Form930Fuel", Flaky)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        profile = gc._profile("BANC", 2020)
    assert (5, False) in calls and (5, True) in calls
    assert len(profile) == len(gc.hours(2020))


def test_form930_starts_july_2018():
    gc._profile("BANC", 2018)
    assert [x[2] for x in FakeForm930Fuel.calls] == list(range(7, 13))


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


def test_unpublished_months_skipped(monkeypatch):
    import generation.fleet
    real = generation.fleet.Form860m

    def form860m(year, month, **kwargs):
        if month > 8:
            raise ValueError(f"{year=} {month=} is not published yet")
        return real(year, month, **kwargs)

    monkeypatch.setattr(generation.fleet, "Form860m", form860m)
    assert len(Hydro("CA", "Stanislaus", 2020)) == 8784


def test_form860m_schema_error_not_hidden(monkeypatch):
    import generation.fleet

    def form860m(year, month, **kwargs):
        return pd.DataFrame({"STATE": ["CA"]})

    monkeypatch.setattr(generation.fleet, "Form860m", form860m)
    with pytest.raises(KeyError):
        Hydro("CA", "Stanislaus", 2020)


def test_clean_removes_spike():
    index = gc.hours(2020)[:744]
    values = pd.Series(np.maximum(0, np.cos(2 * np.pi * (index.hour - 20) / 24)) * 100, index=index)
    values.iloc[300] = 10000.0
    clean = gc._clean(values)
    assert clean.max() <= 100.0
    assert clean.iloc[300] == pytest.approx((values.iloc[299] + values.iloc[301]) / 2)


def test_shape_ignores_form930_spike():
    FakeForm930Fuel.spikes = {("BANC", 2020, 3): 1e6}
    shape = gc._shape("BANC", 2020, 3, "SUN")
    assert shape.max() < 0.01


def test_shape_flat_when_values_cancel(monkeypatch):

    class Cancel(FakeForm930Fuel):
        def __init__(self, year, month=None, **kwargs):
            super().__init__(year, month, **kwargs)
            self["ps_mw"] = np.where(np.arange(len(self)) % 2, 100.0, -99.0)

    monkeypatch.setattr(gc, "Form930Fuel", Cancel)
    shape = gc._shape("BANC", 2020, 1, "PS")
    assert shape.nunique() == 1


@pytest.mark.parametrize("code,negative", [("SUN", False), ("OTH", False), ("BAT", True)])
def test_shape_negative_only_for_storage(monkeypatch, code, negative):

    class Night(FakeForm930Fuel):
        def __init__(self, year, month=None, **kwargs):
            super().__init__(year, month, **kwargs)
            self[f"{code.lower()}_mw"] = np.where(self["sun_mw"] > 0, self["sun_mw"], -1.0)

    monkeypatch.setattr(gc, "Form930Fuel", Night)
    shape = gc._shape("BANC", 2020, 1, code)
    assert shape.sum() == pytest.approx(1.0)
    assert (shape < 0).any() == negative


def test_negative_month_stays_negative():
    shape = gc.allocate(-100.0, np.full(10, 0.1), 50.0)
    assert (shape == -10.0).all()


@pytest.mark.parametrize("energy", [1000.0, -1000.0])
def test_allocate_limit(energy):
    shape = np.zeros(100)
    shape[:5] = 0.2
    values = gc.allocate(energy, shape, 50.0)
    assert values.sum() == pytest.approx(energy)
    assert np.abs(values).max() <= 50.0 + 1e-9
    assert (np.abs(values[:5]) == 50.0).all()


def test_allocate_keeps_shape_within_limit():
    shape = np.linspace(1, 2, 24)
    shape /= shape.sum()
    np.testing.assert_allclose(gc.allocate(240.0, shape, 100.0), 240.0 * shape)
    np.testing.assert_allclose(gc.allocate(240.0, shape, None), 240.0 * shape)


def test_allocate_infeasible_is_flat():
    values = gc.allocate(1000.0, np.full(10, 0.1), 50.0)
    np.testing.assert_allclose(values, 100.0)


def test_limits():
    fleet = pd.DataFrame({"month": [1, 1, 2], "plant": [1, 1, 1],
        "category": ["solar", "battery_storage", "solar"], "nameplate_MW": [10.0, 5.0, 12.0]})
    limit = gc.limits(fleet)
    assert limit(1, 1, "solar") == 10.0
    assert limit(1, 1, "other") == 15.0  # plant total in the month
    assert limit(1, 3, "solar") == 15.0  # largest monthly total
    assert limit(2, 1, "solar") is None


def test_plant_hours_limited_by_nameplate(monkeypatch):
    from conftest import ROWS
    rows = dict(ROWS)
    rows["nameplate_mw"] = [12.1, 53.5, 10.0, 100.0]  # unlimited peak is 15.7 MW
    monkeypatch.setattr("conftest.ROWS", rows)
    data = Solar("CA", "Stanislaus", 2020)
    assert data["solar_MW"].max() == pytest.approx(10.0, abs=1e-3)
    assert data.loc[data.index.hour == 8, "solar_MW"].max() == 0  # still dark at night
    monthly = data["solar_MW"].groupby(data.index.month).sum()
    hours = pd.Series(data.index.month).value_counts().sort_index()
    assert monthly.round(2).tolist() == (5.0 * hours).round(2).tolist()
