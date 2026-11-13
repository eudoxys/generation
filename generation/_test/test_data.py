"""Tests for the repository Data frame (offline: downloads are served from the checkout)"""

import io
import os
import urllib.error

import pandas as pd
import pytest

import generation.data
from generation import Data

REPO_DATA = os.path.join(os.path.dirname(__file__), "..", "..", "data")
DAM_LIST = "hydro/BPA_dams/dam_list.csv"
PREFIX = Data.URL.format(branch=Data.BRANCH, path="")


class FakeResponse(io.BytesIO):
    """`urlopen()` response context manager"""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


@pytest.fixture
def urlopen(monkeypatch):
    """Serve repository data files from the checkout and record the URLs"""
    calls = []

    def fake(url, timeout=None):
        calls.append(url)
        assert url.startswith(PREFIX)
        pathname = os.path.join(REPO_DATA, *url[len(PREFIX):].split("/"))
        if not os.path.exists(pathname):
            raise urllib.error.HTTPError(url, 404, "Not Found", None, None)
        with open(pathname, "rb") as fh:
            return FakeResponse(fh.read())

    monkeypatch.setattr(generation.data.urllib.request, "urlopen", fake)
    return calls


def test_reads_repository_file(urlopen):
    data = Data(DAM_LIST)
    expected = pd.read_csv(os.path.join(REPO_DATA, *DAM_LIST.split("/")))
    pd.testing.assert_frame_equal(pd.DataFrame(data), expected)
    assert urlopen == [PREFIX + DAM_LIST]


def test_cached(urlopen):
    Data(DAM_LIST)
    Data(DAM_LIST)
    assert len(urlopen) == 1


def test_refresh(urlopen):
    Data(DAM_LIST)
    Data(DAM_LIST, refresh=True)
    assert len(urlopen) == 2


def test_read_csv_arguments(urlopen):
    data = Data(DAM_LIST, index_col=0)
    assert data.index.name == pd.read_csv(os.path.join(REPO_DATA, *DAM_LIST.split("/"))).columns[0]


def test_bad_cache_downloaded_again(urlopen):
    Data(DAM_LIST)
    from cache import Cache
    pathname = Cache(package="generation", version=Data.VERSION,
        path=["data", *DAM_LIST.split("/")]).pathname
    with open(pathname, "wb") as fh:
        fh.write(b"\x00\xff not a csv \x00")
    data = Data(DAM_LIST, encoding="utf-8")
    assert len(data) > 0
    assert len(urlopen) == 2


def test_not_found(urlopen):
    with pytest.raises(FileNotFoundError):
        Data("hydro/no_such_file.csv")


def test_download_error(monkeypatch):
    def fail(url, timeout=None):
        raise urllib.error.URLError("offline")
    monkeypatch.setattr(generation.data.urllib.request, "urlopen", fail)
    with pytest.raises(RuntimeError):
        Data(DAM_LIST)


@pytest.mark.parametrize("path", ["", "/etc/passwd.csv", "../pyproject.csv",
    "hydro/../../x.csv", "C:/x.csv", "hydro/README.md"])
def test_invalid_path(path):
    with pytest.raises(ValueError):
        Data(path)


@pytest.mark.parametrize("args, error", [((1,), TypeError), ((DAM_LIST,), TypeError)])
def test_invalid_arguments(args, error):
    with pytest.raises(error):
        Data(*args, refresh="yes")


def test_url():
    assert Data.url("hydro/a b.csv") == PREFIX + "hydro/a%20b.csv"
