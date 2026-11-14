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
   balancing authority does not report it, or the monthly Form 930 total is
   not positive, and for January-June 2018 (`eia.Form930Fuel` starts in July
   2018). Form 930 is read one month at a time; when `eia.Form930Fuel` has
   no data for the balancing authority in a month (e.g., no EIA API key for
   2019 or later, a failed download, or an unknown balancing authority), a
   `UserWarning` is issued and every category in that balancing authority
   and month uses the flat shape. Outlier hours in the Form 930 data (more
   than `SPIKE` times the monthly 1st to 99th percentile range beyond that
   range) are interpolated. Negative values are set to zero except for
   storage (`STORAGE`), and a storage month whose positive and negative
   values nearly cancel (`CANCEL`) uses the flat shape. A plant's hours are
   negative only when its Form 923 monthly net generation is negative.

4. Each plant's hourly MW is limited to its Form 860m nameplate capacity in
   the category and month (`allocate`, `limits`); the excess is moved to the
   other hours of the month in proportion to their shape, so the monthly
   energy still matches Form 923.

An hourly mean MW equals the MWh in that hour, so the plant columns sum to the
Form 923 monthly net generation.

Caveats
-------

  - EIA "state-fuel level increment" estimates (Form 923 plant `99999`) cannot
    be located in a county and are not included.

  - CEMS hourly unit loads, NRC reactor status and the 2018 backfill
    described in `DESIGN.md` are not implemented yet, so those hours use the
    flat shape.

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

FORM930_FIRST_MONTH = (2018,7)
"""First year and month of `eia.Form930Fuel` data"""

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
def _fleet(state:str,county:str,year:int) -> pd.DataFrame:
    """@private Get the Form 860m operating generators in a county in a year

    Returns one row per generator-month with columns `month`, `plant`,
    `category` and `nameplate_MW`.
    """
    data = []
    for month in range(1,13):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                fleet = Fleet(state,county,year,months=month)
        except (ValueError,RuntimeError) as err:
            # `eia.Form860m` raises `ValueError` for a month not published
            # yet and `RuntimeError` for a workbook it cannot download or
            # read; anything else (e.g., a `KeyError` from a schema change)
            # is a bug and is re-raised
            _logger.debug(f"Form 860m {year=} {month=} not available ({err})")
            continue
        data.append(pd.DataFrame({
            "month": month,
            "plant": [int(x) for x in fleet["id"]],
            "category": [category(x,y) for x,y in zip(fleet["fuel"],fleet["gen"])],
            "nameplate_MW": pd.to_numeric(fleet["nameplate_MW"],errors="coerce").values,
            }))
    if not data:
        raise RuntimeError(f"no Form 860m data available for {year=}")
    return pd.concat(data,ignore_index=True)

@functools.cache
def _plants(state:str,county:str,year:int) -> tuple[int]:
    """@private Get the ids of the plants in a county in any month of a year"""
    ids = tuple(sorted(set(_fleet(state,county,year)["plant"])))
    if not ids:
        warnings.warn(f"no generators found in {county} {state} in {year}")
    return ids

def limits(fleet:pd.DataFrame) -> callable:
    """Get the hourly MW limit of the plants in a fleet

    Arguments
    ---------

      - `fleet`: generator-months with columns `month`, `plant`, `category`
        and `nameplate_MW`

    Returns
    -------

      - `callable`: `limit(plant,month,category)` gives the plant's
        nameplate MW in the category and month; when the plant has none
        (e.g., Form 923 and Form 860m assign its fuel differently), the
        plant's total nameplate MW in the month, or else its largest monthly
        total in the year; `None` when the plant is not in the fleet
    """
    fleet = fleet.assign(nameplate_MW=pd.to_numeric(fleet["nameplate_MW"],errors="coerce").fillna(0.0))
    by_category = fleet.groupby(["plant","month","category"])["nameplate_MW"].sum().to_dict()
    by_month = fleet.groupby(["plant","month"])["nameplate_MW"].sum()
    by_plant = by_month.groupby("plant").max().to_dict()
    by_month = by_month.to_dict()
    def limit(plant:int,month:int,name:str) -> float|None:
        for value in (by_category.get((plant,month,name)),by_month.get((plant,month)),by_plant.get(plant)):
            if value is not None and value > 0:
                return float(value)
        return None
    return limit

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
    """@private Get the Form 930 hourly net generation by energy source of a BA

    Returns a frame indexed by UTC hour-beginning `timestamp` with one
    `{code}_mw` column per energy source code (lower case), or `None` when
    no month of the year is available. Each month is read separately (a
    failed download is retried once) so that a month that cannot be read
    leaves only that month flat. Errors other than missing data (e.g., `TypeError` or `KeyError`
    from an `eia` API change) are not caught.
    """
    data = []
    failed = {}
    for month in range(1,13):
        if (year,month) < FORM930_FIRST_MONTH:
            continue # not published, flat silently
        try:
            try:
                data.append(Form930Fuel(year,month,respondent=ba,refresh=refresh))
            except (RuntimeError,OSError) as err:
                # retry a failed download or unreadable cached file once
                _logger.debug(f"retrying Form 930 {ba} {year}-{month:02d} ({err})")
                data.append(Form930Fuel(year,month,respondent=ba,refresh=True))
        except (ValueError,RuntimeError,OSError) as err:
            failed[month] = err
    if failed:
        when = f"{year}" if not data else \
            f"{year} month(s) {','.join(f'{x:02d}' for x in failed)}"
        warnings.warn(f"no Form 930 energy source data for {ba} in {when} "
            f"({list(failed.values())[0]}); using flat shapes")
    if not data:
        return None
    data = pd.concat(data)
    data.index = pd.DatetimeIndex(data.index).tz_convert("UTC")
    return data

SPIKE = 2.0
"""Outlier threshold of a Form 930 hourly value, in multiples of the
monthly 1st to 99th percentile range beyond that range"""

STORAGE = ["BAT","PS"]
"""Form 930 energy source codes whose hourly net generation is negative when
charging; the shapes of other codes use only their non-negative values"""

CANCEL = 0.5
"""Least ratio of the monthly Form 930 total to the total of its absolute
values for which the hourly values are used as a shape"""

def _clean(values:pd.Series) -> pd.Series:
    """@private Remove outliers from a month of Form 930 hourly values

    Values more than `SPIKE` times the 1st to 99th percentile range beyond
    that range (e.g., a single hour reported as 100 times the monthly peak)
    are treated as missing, and missing values are interpolated.
    """
    low,high = values.quantile(0.01),values.quantile(0.99)
    margin = SPIKE * (high - low)
    if np.isfinite(margin) and margin > 0:
        spikes = (values > high + margin) | (values < low - margin)
        if spikes.any():
            _logger.debug(f"removed {spikes.sum()} Form 930 outlier(s) {values[spikes].to_dict()}")
            values = values.mask(spikes)
    return values.interpolate(limit_direction="both")

def _shape(ba:str|None,year:int,month:int,code:str|None,refresh:bool=False) -> pd.Series:
    """@private Get the hourly shape of a BA energy source in a month

    The shape sums to 1 over the month. Outliers are removed first (see
    `SPIKE`), and negative values (e.g., solar plant standby load at night)
    are set to zero except for storage (`STORAGE`), so the shape of a
    non-storage source is never negative. A flat shape is returned when no
    valid Form 930 data is available, or when the monthly total is not
    positive or is small compared to the hourly values (positive and
    negative storage values that nearly cancel, see `CANCEL`).
    """
    index = hours(year)
    index = index[index.month == month]
    flat = pd.Series(1/len(index),index=index)
    if code is None or not isinstance(ba,str) or not ba:
        return flat
    profile = _profile(ba,year,refresh)
    column = f"{code.lower()}_mw"
    if profile is None or column not in profile.columns:
        return flat
    values = profile[column].reindex(index).astype(float)
    if values.notna().sum() == 0:
        return flat
    values = _clean(values)
    if code.upper() not in STORAGE:
        values = values.clip(lower=0)
    total = values.sum()
    if not np.isfinite(total) or total <= 0 or total < CANCEL * values.abs().sum():
        return flat
    return values / total

def allocate(energy:float,shape:pd.Series|np.ndarray,limit:float|None=None) -> np.ndarray:
    """Allocate monthly energy to hours by a shape without exceeding a limit

    Arguments
    ---------

      - `energy`: energy of the month in MWh

      - `shape`: hourly shape of the month (sums to 1)

      - `limit`: largest magnitude of the hourly MW (e.g., the plant
        nameplate capacity), `None` or not positive for no limit

    Returns
    -------

      - `np.ndarray`: hourly MW, summing to `energy`

    Hours above the limit are set to the limit and the excess is moved to the
    other hours in proportion to their shape and remaining headroom. When the
    energy cannot be delivered within the limit (more than `limit` MW in every
    hour), the energy is spread evenly over the month.
    """
    shape = np.asarray(shape,dtype=float)
    values = energy * shape
    if limit is None or not np.isfinite(limit) or limit <= 0:
        return values
    count = len(values)
    if abs(energy) >= limit * count:
        return np.full(count,energy/count)
    for _ in range(100):
        values = np.clip(values,-limit,limit)
        excess = energy - values.sum()
        if abs(excess) <= 1e-9 * max(1.0,abs(energy)):
            return values
        headroom = (limit - values) if excess > 0 else (values + limit)
        weight = headroom * np.clip(np.sign(energy) * shape,0,None)
        if weight.sum() <= 0:
            weight = headroom
        values = values + excess * weight / weight.sum()
    # headroom-proportional allocation always fits within the limit
    values = np.clip(values,-limit,limit)
    excess = energy - values.sum()
    headroom = (limit - values) if excess > 0 else (values + limit)
    return values + excess * headroom / headroom.sum()

def clear():
    """Clear the data held in memory by generation data frames

    Downloaded and computed data is also cached on disk. Use the `refresh`
    argument of the constructors to refresh the disk cache.
    """
    _fleet.cache_clear()
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

    VERSION = 1
    """Cache version (1: Form 930 shapes read by month and cleaned of
    outliers, county names matched without regard to case, plant hours
    limited to nameplate capacity)"""

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
            limit = limits(_fleet(state,county,year))
            for plant,rows in monthly.groupby("plant"):
                values = pd.Series(0.0,index=index)
                for ba,timestamp,energy in zip(rows["ba"],rows["timestamp"],rows["gen_mwh"]):
                    if pd.isna(energy):
                        continue
                    month = pd.Timestamp(timestamp).month
                    shape = _shape(None if pd.isna(ba) else ba,year,month,self.SHAPE,refresh)
                    values.loc[shape.index] += allocate(energy,shape,limit(plant,month,self.CATEGORY))
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
