"""Tests for the Generation data frame and the command line interface

Tests marked `xfail` describe behaviour tracked in open issues; they start
passing (and can be unmarked) once the corresponding fix is merged.
"""

import gzip

import pytest

from generation import Generation
from generation.cli import main, E_OK

COLUMNS = ["region", "county", "sector", "id", "unit", "name", "owner",
    "fuel", "gen", "nameplate_MW", "summer_MW", "winter_MW",
    "latitude", "longitude", "geohash"]


def test_reads_operating_subset(offline):
    Generation(2020, 8)
    assert offline.calls == [(2020, 8, "Operating")]


def test_all_months_by_default(offline):
    Generation(2020)
    assert [m for _, m, _ in offline.calls] == list(range(1, 13))


def test_columns_and_extra_column_dropped():
    data = Generation(2020, 8, states=["CA"])
    assert list(data.columns) == COLUMNS
    assert "UNIT_CODE" not in data.columns


def test_timestamps_per_month():
    data = Generation(2020, [6, 7], states=["CA"])
    stamps = sorted(set(data.index.get_level_values("timestamp")))
    assert [str(x.date()) for x in stamps] == ["2020-06-01", "2020-07-01"]


def test_state_filter():
    data = Generation(2020, 8, states=["CA"])
    assert set(data.index.get_level_values("state")) == {"CA"}
    assert len(data) == 2


def test_geohash():
    data = Generation(2020, 8, states=["CA"])
    assert data["geohash"].iloc[0] == "9qcyxs"


@pytest.mark.parametrize("months", [0, 13, [8, 13]])
def test_invalid_month(months):
    with pytest.raises((AssertionError, ValueError)):
        Generation(2020, months)


def test_cli_csv_file(tmp_path):
    out = tmp_path / "gen.csv"
    assert main("2020", "8", "CA", "-o", str(out)) == E_OK
    lines = out.read_text().splitlines()
    assert lines[0].startswith("state,timestamp")
    assert len(lines) == 3


def test_cli_gzip_file(tmp_path):
    out = tmp_path / "gen.csv.gz"
    assert main("2020", "8", "CA", "-o", str(out)) == E_OK
    assert len(gzip.decompress(out.read_bytes()).decode().splitlines()) == 3


def test_cli_bad_output_name(tmp_path):
    assert main("2020", "8", "CA", "-o", str(tmp_path / "gen.txt")) != E_OK


@pytest.mark.xfail(reason="#1 month and states should be optional", raises=SystemExit)
def test_cli_year_only():
    assert main("2020") == E_OK


@pytest.mark.xfail(reason="#2 comma-separated months", raises=SystemExit)
def test_cli_month_list(offline):
    assert main("2020", "6,7", "CA") == E_OK
    assert [m for _, m, _ in offline.calls] == [6, 7]


@pytest.mark.xfail(reason="#4 index should not depend on how states is passed")
def test_index_shape_consistent():
    expected = ["state", "county", "geohash", "timestamp"]
    for states in ["CA", ["CA"], None]:
        assert list(Generation(2020, 8, states=states).index.names) == expected


@pytest.mark.xfail(reason="#5 missing state should not raise KeyError")
def test_missing_state():
    with pytest.warns(UserWarning):
        assert len(Generation(2020, 8, states=["TX"])) == 0
