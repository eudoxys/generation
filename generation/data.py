"""Repository data accessor

The `Data` data frame reads a CSV file from the `data/` folder of the
`eudoxys/generation` source repository. The data files are not installed
with the package. The first time a file is requested, it is downloaded from
GitHub and saved in the Eudoxys `cache`; later requests read the cached
copy.

Example
-------

To get the list of BPA dams run the following:

    from generation import Data
    Data("hydro/BPA_dams/dam_list.csv")

To read an hourly file with a timestamp index run the following:

    Data("hydro/BPA_dams/USACE_CWMS_hourly/BON_Bonneville_hourly_2018_2022_UTC.csv",
        index_col="datetime_utc",parse_dates=True)

Keyword arguments other than `refresh` are passed to `pandas.read_csv()`.
See `data/README.md` files in the repository for each dataset's columns,
units and time convention.
"""

import os
import logging
import posixpath
import tempfile
import urllib.error
import urllib.parse
import urllib.request

import pandas as pd

from cache import Cache

_logger = logging.getLogger(__file__)

class Data(pd.DataFrame):
    """Repository data frame

    The index and columns are those of the CSV file, as read by
    `pandas.read_csv()` with the keyword arguments given to the constructor.
    """

    URL = "https://raw.githubusercontent.com/eudoxys/generation/{branch}/data/{path}"
    """URL template of a repository data file; `{branch}` and `{path}` are
    filled from `BRANCH` and the `path` argument"""

    BRANCH = "main"
    """Repository branch (or tag) from which data files are downloaded"""

    CACHEDIR = None
    """Cache folder (`None` uses the `cache` package default)"""

    VERSION = 0
    """Cache version of repository data files"""

    TIMEOUT = 60
    """Download timeout in seconds"""

    EXTENSIONS = (".csv",".csv.gz")
    """Data file extensions that can be read"""

    def __init__(self,
        path:str,
        *,
        refresh:bool=False,
        **kwargs,
        ):
        """Repository data frame constructor

        Arguments
        ---------

          - `path`: path of the file relative to the repository `data/`
            folder, using `/` separators (e.g.,
            `"hydro/BPA_dams/dam_list.csv"`)

          - `refresh`: download the file again even if it is cached

          - `**kwargs`: keyword arguments passed to `pandas.read_csv()`

        Raises
        ------

          - `TypeError`: `path` is not a string or `refresh` is not a bool

          - `ValueError`: `path` is not a relative path to a CSV file inside
            `data/`

          - `FileNotFoundError`: the file is not in the repository

          - `RuntimeError`: the file cannot be downloaded or read
        """
        path = self._check(path)
        if not isinstance(refresh,bool):
            raise TypeError(f"{refresh=} is not a bool")

        if self.CACHEDIR:
            Cache.CACHEDIR = self.CACHEDIR
        cache = Cache(package="generation",version=self.VERSION,
            path=["data",*path.split("/")])

        # read the cached copy (os.path.exists is used instead of
        # cache.exists() so the cache archives are not searched)
        data = None
        if os.path.exists(cache.pathname) and not refresh:
            try:
                data = pd.read_csv(cache.pathname,**kwargs)
                _logger.debug(f"loaded {cache.pathname}")
            except Exception as err: # pylint: disable=broad-exception-caught
                _logger.debug(f"unable to read {cache.pathname} ({err}); downloading again")
                cache.delete()

        # download and cache the repository copy
        if data is None:
            url = self.url(path)
            self._download(url,cache.pathname)
            try:
                data = pd.read_csv(cache.pathname,**kwargs)
            except Exception as err:
                cache.delete()
                raise RuntimeError(f"unable to read {url} ({err})") from err
            _logger.debug(f"saved {url} to {cache.pathname}")

        super().__init__(data)

    @classmethod
    def url(cls,path:str) -> str:
        """Get the download URL of a repository data file

        Arguments
        ---------

          - `path`: path of the file relative to the repository `data/` folder

        Returns
        -------

          - `str`: URL of the file on `BRANCH`
        """
        path = cls._check(path)
        return cls.URL.format(branch=cls.BRANCH,path=urllib.parse.quote(path))

    @classmethod
    def _check(cls,path:str) -> str:
        """@private Check a data file path and return it normalized"""
        if not isinstance(path,str):
            raise TypeError(f"{path=} is not a string")
        norm = posixpath.normpath(path.replace("\\","/"))
        if not path or norm.startswith(("/","../")) or norm in (".","..") or ":" in norm:
            raise ValueError(f"{path=} is not a relative path inside data/")
        if not norm.endswith(cls.EXTENSIONS):
            raise ValueError(f"{path=} is not a {' or '.join(cls.EXTENSIONS)} file")
        return norm

    @classmethod
    def _download(cls,url:str,pathname:str):
        """@private Download a file to a cache pathname

        The file is written to a temporary file first so an interrupted
        download never leaves a partial cache file.
        """
        _logger.debug(f"downloading {url}")
        try:
            with urllib.request.urlopen(url,timeout=cls.TIMEOUT) as response:
                content = response.read()
        except urllib.error.HTTPError as err:
            if err.code == 404:
                raise FileNotFoundError(f"{url} not found") from err
            raise RuntimeError(f"unable to download {url} (HTTP error {err.code})") from err
        except (urllib.error.URLError,OSError) as err:
            raise RuntimeError(f"unable to download {url} ({err})") from err
        handle,tmpname = tempfile.mkstemp(dir=os.path.dirname(pathname),suffix=".tmp")
        try:
            with os.fdopen(handle,"wb") as fh:
                fh.write(content)
            os.replace(tmpname,pathname)
        finally:
            if os.path.exists(tmpname):
                os.unlink(tmpname)

if __name__ == "__main__":

    print(Data("hydro/BPA_dams/dam_list.csv"))
