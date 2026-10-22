"""Tests for the Fleet data frame and the command line interface"""

import gzip

import pytest

from generation import Fleet
from generation.cli import main, E_OK

INDEX = ["state", "county", "geohash", "timestamp"]
COLUMNS = ["region", "sector", "id", "unit", "name", "owner",
    "fuel", "gen", "nameplate_MW", "summer_MW", "winter_MW",
    "latitude", "longitude"]


def test_reads_operating_subset(offline):
    Fleet(year=2020, months=8)
    assert offline.calls == [(2020, 8, "Operating")]


def test_all_months_by_default(offline):
    Fleet(year=2020)
    assert [m for _, m, _ in offline.calls] == list(range(1, 13))


def test_year_required():
    with pytest.raises(TypeError):
        Fleet("CA")


def test_columns_and_extra_column_dropped():
    data = Fleet("CA", year=2020, months=8)
    assert list(data.index.names) == INDEX
    assert list(data.columns) == COLUMNS
    assert "UNIT_CODE" not in data.columns


def test_timestamps_per_month():
    data = Fleet("CA", year=2020, months=[6, 7])
    stamps = sorted(set(data.index.get_level_values("timestamp")))
    assert [str(x.date()) for x in stamps] == ["2020-06-01", "2020-07-01"]


def test_state_filter():
    data = Fleet("CA", year=2020, months=8)
    assert set(data.index.get_level_values("state")) == {"CA"}
    assert len(data) == 3


def test_county_filter():
    data = Fleet("CA", "Stanislaus", 2020, months=8)
    assert set(data.index.get_level_values("county")) == {"Stanislaus"}
    assert sorted(data["id"]) == [151, 152]


def test_geohash():
    data = Fleet("CA", year=2020, months=8)
    assert data.index.get_level_values("geohash")[0] == "9qcyxs"


@pytest.mark.parametrize("months", [0, 13, [8, 13]])
def test_invalid_month(months):
    with pytest.raises(ValueError):
        Fleet(year=2020, months=months)


@pytest.mark.parametrize("months", [8.0, True, ["8"]])
def test_non_integer_month(months):
    with pytest.raises(TypeError):
        Fleet(year=2020, months=months)


@pytest.mark.parametrize("state", [("CA",), ["CA", 1]])
def test_invalid_states(state):
    with pytest.raises(TypeError):
        Fleet(state, year=2020, months=8)


def test_cli_csv_file(tmp_path):
    out = tmp_path / "gen.csv"
    assert main("2020", "8", "CA", "-o", str(out)) == E_OK
    lines = out.read_text().splitlines()
    assert lines[0].startswith("state,county,geohash,timestamp,")
    assert len(lines) == 4


def test_cli_gzip_file(tmp_path):
    out = tmp_path / "gen.csv.gz"
    assert main("2020", "8", "CA", "-o", str(out)) == E_OK
    assert len(gzip.decompress(out.read_bytes()).decode().splitlines()) == 4


def test_cli_bad_output_name(tmp_path):
    assert main("2020", "8", "CA", "-o", str(tmp_path / "gen.txt")) != E_OK


def test_cli_year_only():
    assert main("2020") == E_OK


def test_cli_month_list(offline):
    assert main("2020", "6,7", "CA") == E_OK
    assert [m for _, m, _ in offline.calls] == [6, 7]


def test_cli_county(tmp_path):
    out = tmp_path / "gen.csv"
    assert main("2020", "8", "CA", "-C", "Stanislaus", "-o", str(out)) == E_OK
    assert len(out.read_text().splitlines()) == 3


def test_index_shape_consistent():
    expected = ["state", "county", "geohash", "timestamp"]
    for state in ["CA", ["CA"], None]:
        assert list(Fleet(state, year=2020, months=8).index.names) == expected


def test_missing_state():
    with pytest.warns(UserWarning):
        assert len(Fleet("TX", year=2020, months=8)) == 0


def test_missing_county():
    with pytest.warns(UserWarning):
        assert len(Fleet("CA", "Kern", 2020, months=8)) == 0
