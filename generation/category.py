"""Generation category base classes

All generation data frames in this package are constructed the same way,

    Class(state,county,year)

and return hourly net generation in MW for the county, indexed by the UTC
hour-beginning `timestamp` of every hour of the year.

There are two kinds of generation data frames:

  - `Category` data frames (e.g., `generation.coal.Coal`) are constructed from
    individual plants. They have one `plant_{id}_MW` column for each
    contributing plant and a `{category}_MW` total column.

  - `Combination` data frames (e.g., `generation.dispatchable.Dispatchable`)
    are constructed from other generation data frames. They keep the columns
    of each contributing data frame (only the total column of a `Category`)
    and add their own total column.

Method
------

The hourly net generation of a category is computed as follows:

```mermaid
flowchart LR
    F860M[Form 860m] -->|plants in county| Plants
    F923[Form 923] -->|monthly net MWh| Plants
    Plants -->|category| Monthly[plant-month energy]
    F930[Form 930 by fuel] -->|BA hourly shape| Hourly
    Monthly --> Hourly[plant-hour MW]
    Hourly --> Columns["plant_{id}_MW, {category}_MW"]
```

1. The plants in the county are the plants listed in any month of the
   Form 860m operating generator inventory for the year.

2. Each plant's monthly net generation by prime mover and energy source is
   taken from Form 923 and assigned to a category using
   `generation.fuels.category`.

3. The monthly energy is shaped into hours using the hourly Form 930 net
   generation of the plant's balancing authority for the category's energy
   source (see `generation.fuels.SHAPES`), normalized to sum to 1 over the
   month. A flat shape is used when the category has no Form 930 code, the
   balancing authority does not report it, the month is before July 2018, or
   the monthly Form 930 total is not positive.

An hourly mean MW equals the MWh in that hour, so the plant columns sum to the
Form 923 monthly net generation.

Caveats
-------

  - EIA "state-fuel level increment" estimates (Form 923 plant `99999`) cannot
    be located in a county and are not included.

  - CEMS hourly unit loads, NRC reactor status and the January-June 2018
    backfill described in `DESIGN.md` are not implemented yet, so those hours
    use the flat shape.

  - Net generation can be negative, e.g., storage, and plants whose station
    use exceeds their output.
"""

import functools
import logging
import numbers
import warnings

import numpy as np
import pandas as pd

from eia import Form923, Form930Fuel
from cache import Cache

from generation.fleet import Fleet
from generation.fuels import CATEGORIES, SHAPES, category

_logger = logging.getLogger(__file__)

FIRST_YEAR = 2018
"""First year of generation data"""

PRECISION = 3
"""Precision of generation data in MW"""

def hours(year:int) -> pd.DatetimeIndex:
    """Get the UTC hour-beginning timestamps of a year

    Arguments
    ---------

      - `year`: calendar year

    Returns
    -------

      - `pd.DatetimeIndex`: 8760 (or 8784) hourly timestamps named `timestamp`
    """
    return pd.date_range(f"{year}-01-01",f"{year+1}-01-01",
        freq="h",inclusive="left",tz="UTC",name="timestamp")

def _check(state:str,county:str,year:int):
    """@private Check the constructor arguments"""
    if not isinstance(state,str) or len(state) != 2:
        raise ValueError(f"{state=} is not a two-letter state code")
    if not isinstance(county,str) or not county:
        raise ValueError(f"{county=} is not a county name")
    if not isinstance(year,numbers.Integral) or isinstance(year,bool):
        raise TypeError(f"{year=} is not an integer")
    if year < FIRST_YEAR:
        raise ValueError(f"{year=} is before {FIRST_YEAR}")

@functools.cache
def _plants(state:str,county:str,year:int) -> tuple[int]:
    """@private Get the ids of the plants in a county in any month of a year"""
    ids = set()
    found = False
    for month in range(1,13):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                data = Fleet(state,county,year,months=month)
        except Exception as err: # pylint: disable=broad-exception-caught
            _logger.debug(f"Form 860m {year=} {month=} not available ({err})")
            continue
        found = True
        ids.update(int(x) for x in data["id"])
    if not found:
        raise RuntimeError(f"no Form 860m data available for {year=}")
    if not ids:
        warnings.warn(f"no generators found in {county} {state} in {year}")
    return tuple(sorted(ids))

@functools.cache
def _monthly(state:str,year:int,refresh:bool=False) -> pd.DataFrame:
    """@private Get the Form 923 monthly net generation of the plants in a state

    Returns a data frame with columns `timestamp`, `ba`, `plant`, `category`
    and `gen_mwh`.
    """
    data = Form923(year,states=[state],by="plant",increments=False,refresh=refresh).reset_index()
    data["category"] = [category(x,y) for x,y in zip(data["fuel"],data["pm"])]
    data["plant"] = data["plant"].astype(int)
    return data[["timestamp","ba","plant","category","gen_mwh"]]

@functools.cache
def _profile(ba:str,year:int,refresh:bool=False) -> pd.DataFrame|None:
    """@private Get the Form 930 hourly net generation by energy source of a BA"""
    try:
        data = Form930Fuel(ba,year,refresh=refresh)
    except Exception as err: # pylint: disable=broad-exception-caught
        warnings.warn(f"no Form 930 energy source data for {ba} in {year} ({err}); using flat shapes")
        return None
    data = data.set_index("timestamp")
    data.index = pd.DatetimeIndex(data.index).tz_convert("UTC")
    return data

def _shape(ba:str|None,year:int,month:int,code:str|None,refresh:bool=False) -> pd.Series:
    """@private Get the hourly shape of a BA energy source in a month

    The shape sums to 1 over the month. A flat shape is returned when no valid
    Form 930 data is available.
    """
    index = hours(year)
    index = index[index.month == month]
    flat = pd.Series(1/len(index),index=index)
    if code is None or not isinstance(ba,str) or not ba:
        return flat
    profile = _profile(ba,year,refresh)
    if profile is None or f"{code}_MW" not in profile.columns:
        return flat
    values = profile[f"{code}_MW"].reindex(index).astype(float)
    if values.notna().sum() == 0:
        return flat
    values = values.interpolate(limit_direction="both")
    total = values.sum()
    if not np.isfinite(total) or total <= 0:
        return flat
    return values / total

def clear():
    """Clear the data held in memory by generation data frames

    Downloaded and computed data is also cached on disk. Use the `refresh`
    argument of the constructors to refresh the disk cache.
    """
    _plants.cache_clear()
    _monthly.cache_clear()
    _profile.cache_clear()

class Category(pd.DataFrame):
    """Generation category data frame base class

    Index
    -----

      - `timestamp`: UTC hour-beginning timestamp

    Columns
    -------

      - `plant_{id}_MW`: net generation of EIA plant `id` in this category

      - `{category}_MW`: total net generation of this category in the county

    Subclasses set `CATEGORY` to one of `generation.fuels.CATEGORIES`.
    """

    CACHEDIR = None
    """Cache folder (`None` uses the `cache` package default)"""

    VERSION = 0
    """Cache version"""

    CATEGORY = None
    """Generation category"""

    COLUMN = None
    """Total column name (`{category}_MW`)"""

    SHAPE = None
    """Form 930 energy source code used to shape monthly energy (`None` is flat)"""

    def __init_subclass__(cls,**kwargs):
        super().__init_subclass__(**kwargs)
        if cls.CATEGORY is not None:
            assert cls.CATEGORY in CATEGORIES, f"{cls.CATEGORY=} is not valid"
            cls.COLUMN = f"{cls.CATEGORY}_MW"
            cls.SHAPE = SHAPES[cls.CATEGORY]

    def __init__(self,
        state:str,
        county:str,
        year:int,
        *,
        refresh:bool=False,
        ):
        """Construct a generation category data frame

        Arguments
        ---------

          - `state`: two-letter state code (e.g., `"CA"`)

          - `county`: county name as given in Form 860m (e.g., `"Kern"`)

          - `year`: calendar year (2018 or later)

          - `refresh`: refresh cached data
        """
        assert self.CATEGORY is not None, "Category cannot be constructed directly"
        _check(state,county,year)
        year = int(year)

        if self.CACHEDIR:
            Cache.CACHEDIR = self.CACHEDIR
        cache = Cache(package="generation",version=self.VERSION,
            path=[state,county,str(year),f"{self.CATEGORY}.csv.gz"])

        data = None
        if cache.exists() and not refresh:
            try:
                data = pd.read_csv(cache.pathname,index_col=[0])
                data.index = pd.DatetimeIndex(pd.to_datetime(data.index,utc=True),name="timestamp")
                _logger.debug(f"loaded {cache.pathname}")
            except Exception as err: # pylint: disable=broad-exception-caught
                _logger.debug(f"unable to read {cache.pathname} ({err})")
                data = None
                cache.delete()

        if data is None:
            data = self._build(state,county,year,refresh)
            data.to_csv(cache.pathname,index=True,header=True,compression="gzip")
            _logger.debug(f"saved {cache.pathname}")

        super().__init__(data)

    def _build(self,state:str,county:str,year:int,refresh:bool) -> pd.DataFrame:
        """@private Compute the hourly net generation of the plants in a county"""
        index = hours(year)
        columns = {}
        plants = _plants(state,county,year)
        if plants:
            monthly = _monthly(state,year,refresh)
            monthly = monthly.loc[monthly["plant"].isin(plants)
                & (monthly["category"] == self.CATEGORY)]
            monthly = monthly.groupby(["plant","ba","timestamp"],dropna=False)["gen_mwh"].sum().reset_index()
            for plant,rows in monthly.groupby("plant"):
                values = pd.Series(0.0,index=index)
                for ba,timestamp,energy in zip(rows["ba"],rows["timestamp"],rows["gen_mwh"]):
                    if pd.isna(energy):
                        continue
                    shape = _shape(None if pd.isna(ba) else ba,year,
                        pd.Timestamp(timestamp).month,self.SHAPE,refresh)
                    values.loc[shape.index] += energy * shape
                columns[f"plant_{plant}_MW"] = values
        data = pd.DataFrame(columns,index=index)
        data[self.COLUMN] = data.sum(axis=1)
        return data.round(PRECISION)

    @classmethod
    def makeargs(cls,**kwargs) -> dict:
        """@private Return the kwargs accepted by this class constructor"""
        return {x:y for x,y in kwargs.items() if x in cls.__init__.__annotations__}

class Combination(pd.DataFrame):
    """Combined generation data frame base class

    Index
    -----

      - `timestamp`: UTC hour-beginning timestamp

    Columns
    -------

    The columns of each data frame in `PARTS` (only the total column of a
    `Category`), followed by `COLUMN`, the sum of the totals of the parts.

    Subclasses set `PARTS` and `COLUMN`.
    """

    PARTS = []
    """Generation data frame classes combined"""

    COLUMN = None
    """Total column name"""

    def __init__(self,
        state:str,
        county:str,
        year:int,
        *,
        refresh:bool=False,
        ):
        """Construct a combined generation data frame

        Arguments
        ---------

          - `state`: two-letter state code (e.g., `"CA"`)

          - `county`: county name as given in Form 860m (e.g., `"Kern"`)

          - `year`: calendar year (2018 or later)

          - `refresh`: refresh cached data
        """
        assert self.COLUMN is not None, "Combination cannot be constructed directly"
        _check(state,county,year)

        parts = []
        for part in self.PARTS:
            data = part(state,county,year,refresh=refresh)
            if issubclass(part,Category):
                data = data[[part.COLUMN]]
            parts.append(pd.DataFrame(data))
        data = pd.concat(parts,axis=1)
        data[self.COLUMN] = data[[x.COLUMN for x in self.PARTS]].sum(axis=1)

        super().__init__(data.round(PRECISION))

    @classmethod
    def makeargs(cls,**kwargs) -> dict:
        """@private Return the kwargs accepted by this class constructor"""
        return {x:y for x,y in kwargs.items() if x in cls.__init__.__annotations__}
