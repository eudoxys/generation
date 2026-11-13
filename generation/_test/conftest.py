"""Test fixtures: replace EIA downloads with small local tables

Set `GENERATION_CACHEDIR` to keep downloaded data in a folder other than the
`cache` package default (inside site-packages, so lost on every fresh
install, e.g., in CI). The autouse `offline` fixture still points each fast
test at its own temporary cache.
"""

import os
import sys
import types

import numpy as np
import pandas as pd
import pytest

from cache import Cache

if os.environ.get("GENERATION_CACHEDIR"):
    Cache.CACHEDIR = os.environ["GENERATION_CACHEDIR"]

ROWS = {
    # same names as `eia.Form860m` (0.0.1); `plant` and `generator` are
    # index levels there
    "state": ["CA", "CA", "CA", "WA"],
    "ba": ["CISO", "BANC", "BANC", "BPAT"],
    "county": ["Placer", "Stanislaus", "Stanislaus", "King"],
    "sector": ["IPP Non-CHP", "Electric Utility", "IPP Non-CHP", "Electric Utility"],
    "plant": [34, 151, 152, 900],
    "generator": ["1P", "1", "PV1", "A"],
    "plant_name": ["Plant A", "Plant B", "Plant D", "Plant C"],
    "owner": [1001, 1002, 1004, 1003],  # entity id, not used by Fleet
    "owner_name": ["Owner A", "Owner B", "Owner D", "Owner C"],
    "fuel": ["NG", "WAT", "SUN", "WAT"],
    "pm": ["CT", "HY", "PV", "HY"],
    "nameplate_mw": [12.1, 53.5, 20.0, 100.0],
    "summer_mw": [12.1, 53.5, 20.0, 100.0],
    "winter_mw": [12.1, 53.5, 20.0, 100.0],
    "latitude": [39.134259, 37.629360, 37.5, 47.6],
    "longitude": [-120.9533, -120.9314, -120.9, -122.3],
    "unit": ["", "", "", ""],  # extra column that Fleet must drop
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

    def __init__(self, year, month, *, subset=None, raw=False, refresh=False):
        FakeForm860m.calls.append((year, month, subset))
        data = pd.DataFrame(ROWS)
        data.insert(0, "timestamp", pd.Timestamp(year=year, month=month, day=1, tz="UTC"))
        super().__init__(data.set_index(["timestamp", "plant", "generator"]))


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

    Matches the `eia` signature `Form930Fuel(year,month=None,*,respondent)`:
    indexed by UTC hour-beginning `timestamp`, with lower-case `{code}_mw`
    columns. BANC reports a diurnal `sun_mw` and a constant `wat_mw`; other
    respondents raise `ValueError` like an invalid respondent code does.
    """

    calls = []

    def __init__(self, year, month=None, *, respondent, fuels=None, raw=False, refresh=False):
        FakeForm930Fuel.calls.append((respondent, year))
        if respondent != "BANC":
            raise ValueError(f"respondent={respondent!r} is not a valid respondent code")
        index = pd.DatetimeIndex(hours(year), name="timestamp")
        sun = np.maximum(0, np.cos(2 * np.pi * (index.hour - 20) / 24))  # peak at 20:00Z
        super().__init__({"sun_mw": 100 * sun, "wat_mw": 50.0}, index=index)


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
