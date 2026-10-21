"""Test fixtures: replace EIA Form 860m downloads with a small local table"""

import sys
import types

import pandas as pd
import pytest

ROWS = {
    "STATE": ["CA", "CA", "WA"],
    "BA_CODE": ["CISO", "BANC", "BPAT"],
    "COUNTY": ["Placer", "Stanislaus", "King"],
    "SECTOR": ["IPP Non-CHP", "Electric Utility", "Electric Utility"],
    "ID": [34, 151, 900],
    "GENERATOR_ID": ["1P", "1", "A"],
    "NAME": ["Plant A", "Plant B", "Plant C"],
    "OWNER_NAME": ["Owner A", "Owner B", "Owner C"],
    "ENERGY_SOURCE_CODE": ["NG", "WAT", "WAT"],
    "PRIME_MOVER_CODE": ["CT", "HY", "HY"],
    "NAMEPLATE_MW": [12.1, 53.5, 100.0],
    "SUMMER_MW": [12.1, 53.5, 100.0],
    "WINTER_MW": [12.1, 53.5, 100.0],
    "LAT": [39.134259, 37.629360, 47.6],
    "LON": [-120.9533, -120.9314, -122.3],
    "UNIT_CODE": ["", "", ""],  # extra column that Generation must drop
}


class FakeForm860m(pd.DataFrame):
    """Offline stand-in for `eia.Form860m`"""

    calls = []

    def __init__(self, year, month, subset=None, refresh=None, raw=None):
        FakeForm860m.calls.append((year, month, subset))
        super().__init__(ROWS)


# allow the suite to run where the eia package isn't installed
try:
    import eia  # pylint: disable=unused-import
except ImportError:
    _eia = types.ModuleType("eia")
    _eia.Form860m = FakeForm860m
    sys.modules["eia"] = _eia


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    """Never download from EIA during tests"""
    import generation.generation  # pylint: disable=import-outside-toplevel
    FakeForm860m.calls = []
    monkeypatch.setattr(generation.generation, "Form860m", FakeForm860m)
    monkeypatch.setattr(sys, "argv", ["generation"])
    return FakeForm860m
