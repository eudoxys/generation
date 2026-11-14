"""Tests of the WECC 240 node file builder `data/wecc/build_nodes.py` (offline)"""

import os
import logging
import importlib.util

import pandas as pd
import pytest

from generation.fuels import CATEGORIES

PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "wecc", "build_nodes.py")

COUNTIES = ["Placer CA", "Sacremento CA", "Stanislaus CA", "King WA", "Lea NM"]


@pytest.fixture
def nodes():
    """Load the builder"""
    spec = importlib.util.spec_from_file_location("build_nodes", PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def mapping(tmp_path):
    """A small county-to-node map in the wecc240 format"""
    pathname = tmp_path / "county_node_map.csv"
    pd.DataFrame({
        "county_st": ["Placer CA", "Sacramento CA", "Stanislaus CA", "King WA"],
        "gen": ["9qcaaa", "9qcaaa", "9q9bbb", "c23ccc"],
        "load": ["x", "x", "y", "z"],
        "any": ["x", "x", "y", "z"],
    }).to_csv(pathname, index=False)
    return str(pathname)


@pytest.fixture
def counties(tmp_path):
    """County files in the build_wecc.py format"""
    folder = tmp_path / "counties"
    folder.mkdir()
    index = pd.date_range("2020-01-01", periods=48, freq="h", tz="UTC")
    index = pd.Index(index.strftime("%Y-%m-%d %H:%M:%S+00:00"), name="timestamp")
    for kind in ("capacity", "actual"):
        for category in CATEGORIES:
            data = pd.DataFrame({x: [float(n + 1)] * len(index) for n, x in enumerate(COUNTIES)}, index=index)
            data.to_csv(folder / f"{kind}_{category}.csv.gz", compression="gzip")
    return str(folder)


def test_weights(nodes, mapping):
    weight = nodes.weights(mapping)
    assert list(weight.columns) == ["9q9bbb", "9qcaaa", "c23ccc"]
    assert (weight.sum(axis=1) == 1).all()
    assert weight.loc["Sacramento CA", "9qcaaa"] == 1


def test_build(nodes, mapping, counties, tmp_path, caplog):
    output = tmp_path / "nodes"
    with caplog.at_level(logging.WARNING):
        files = nodes.build(counties, str(output), mapping)
    assert sorted(files) == sorted(f"{x}_{y}" for x in ("capacity", "actual") for y in CATEGORIES)
    assert "Lea NM" in caplog.text
    for name, pathname in files.items():
        assert os.path.basename(pathname) == f"node_{name}.csv.gz"
        data = pd.read_csv(pathname, index_col="timestamp")
        assert list(data.columns) == ["9q9bbb", "9qcaaa", "c23ccc"]
        assert len(data) == 48
        assert data.index[0] == "2020-01-01 00:00:00+00:00"
        # Placer (1) + Sacramento via alias (2); Stanislaus 3; King 4; Lea dropped
        assert (data["9qcaaa"] == 3).all()
        assert (data["9q9bbb"] == 3).all()
        assert (data["c23ccc"] == 4).all()
