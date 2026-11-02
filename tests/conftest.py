"""Test fixtures: replace EIA downloads with small local tables"""

import sys
import types

import numpy as np
import pandas as pd
import pytest

ROWS = {
    "STATE": ["CA", "CA", "CA", "WA"],
    "BA_CODE": ["CISO", "BANC", "BANC", "BPAT"],
    "COUNTY": ["Placer", "Stanislaus", "Stanislaus", "King"],
    "SECTOR": ["IPP Non-CHP", "Electric Utility", "IPP Non-CHP", "Electric Utility"],
    "ID": [34, 151, 152, 900],
    "GENERATOR_ID": ["1P", "1", "PV1", "A"],
    "NAME": ["Plant A", "Plant B", "Plant D", "Plant C"],
    "OWNER_NAME": ["Owner A", "Owner B", "Owner D", "Owner C"],
    "ENERGY_SOURCE_CODE": ["NG", "WAT", "SUN", "WAT"],
    "PRIME_MOVER_CODE": ["CT", "HY", "PV", "HY"],
    "NAMEPLATE_MW": [12.1, 53.5, 20.0, 100.0],
    "SUMMER_MW": [12.1, 53.5, 20.0, 100.0],
    "WINTER_MW": [12.1, 53.5, 20.0, 100.0],
    "LAT": [39.134259, 37.629360, 37.5, 47.6],
    "LON": [-120.9533, -120.9314, -120.9, -122.3],
    "UNIT_CODE": ["", "", "", ""],  # extra column that Fleet must drop
}

PLANTS = [
    # state, ba, plant, pm, fuel, average MW
    ("CA", "CISO", 34, "CT", "NG", 10.0),
    ("CA", "BANC", 151, "HY", "WAT", 30.0),
    ("CA", "BANC", 152, "PV", "SUN", 5.0),
    ("CA", "BANC", 99999, "ST", "NG", 1.0),  # state-fuel increment
    ("WA", "BPAT", 900, "HY", "WAT", 80.0),
]
"""Form 923 test plants"""


def hours(year, month=None):
    """Hour-beginning UTC timestamps of a year (or month)"""
    index = pd.date_range(f"{year}-01-01", f"{year+1}-01-01", freq="h",
        inclusive="left", tz="UTC", name="timestamp")
    return index if month is None else index[index.month == month]


class FakeForm860m(pd.DataFrame):
    """Offline stand-in for `eia.Form860m`"""

    calls = []

    def __init__(self, year, month, subset=None, refresh=None, raw=None):
        FakeForm860m.calls.append((year, month, subset))
        super().__init__(ROWS)


class FakeForm923(pd.DataFrame):
    """Offline stand-in for `eia.Form923(by="plant")`"""

    calls = []

    def __init__(self, year, month=None, states=None, bas=None, fuels=None, *,
            by="ba", plants=None, increments=True, refresh=False, **kwargs):
        FakeForm923.calls.append((year, states, by, increments))
        rows = []
        for mon in range(1, 13):
            timestamp = pd.Timestamp(year=year, month=mon, day=1, tz="UTC")
            for state, ba, plant, pm, fuel, mw in PLANTS:
                if states is not None and state not in states:
                    continue
                if not increments and plant == 99999:
                    continue
                rows.append((timestamp, state, ba, plant, pm, fuel, mw * len(hours(year, mon))))
        data = pd.DataFrame(rows, columns=["timestamp", "state", "ba", "plant", "pm", "fuel", "gen_mwh"])
        super().__init__(data.set_index(["timestamp", "state", "ba", "plant", "pm", "fuel"]))


class FakeForm930Fuel(pd.DataFrame):
    """Offline stand-in for `eia.Form930Fuel`

    BANC reports a diurnal `SUN_MW` and a constant `WAT_MW`; other
    respondents are not available.
    """

    calls = []

    def __init__(self, respondent, year, month=None, *, fuels=None, refresh=False):
        FakeForm930Fuel.calls.append((respondent, year))
        if respondent != "BANC":
            raise AssertionError(f"{respondent=} is not valid")
        index = hours(year)
        sun = np.maximum(0, np.cos(2 * np.pi * (index.hour - 20) / 24))  # peak at 20:00Z
        super().__init__({"timestamp": index, "SUN_MW": 100 * sun, "WAT_MW": 50.0})


# allow the suite to run where the eia package isn't installed
try:
    import eia  # pylint: disable=unused-import
except ImportError:
    _eia = types.ModuleType("eia")
    _eia.Form860m = FakeForm860m
    _eia.Form923 = FakeForm923
    _eia.Form930Fuel = FakeForm930Fuel
    sys.modules["eia"] = _eia


@pytest.fixture(autouse=True)
def offline(monkeypatch, tmp_path):
    """Never download from EIA and never write to the real cache during tests"""
    # pylint: disable=import-outside-toplevel
    import generation.fleet
    import generation.category
    from cache import Cache
    FakeForm860m.calls = []
    FakeForm923.calls = []
    FakeForm930Fuel.calls = []
    monkeypatch.setattr(generation.fleet, "Form860m", FakeForm860m)
    monkeypatch.setattr(generation.category, "Form923", FakeForm923)
    monkeypatch.setattr(generation.category, "Form930Fuel", FakeForm930Fuel)
    monkeypatch.setattr(Cache, "CACHEDIR", str(tmp_path / "cache"))
    monkeypatch.setattr(sys, "argv", ["generation"])
    generation.category.clear()
    yield FakeForm860m
    generation.category.clear()
