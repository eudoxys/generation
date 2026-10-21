"""Generation fleet data accessor

The `Fleet` data frame collects generator fleet data from EIA Form 860m.

Example
-------

To select the generators in California in August 2020 run the following:

    from generation import Fleet
    Fleet("CA",year=2020,months=8)

which outputs the following

                              region          county  ... longitude  geohash
    timestamp                                         ...                   
    2020-08-01 00:00:00+00:00   CISO          Placer  ... -120.9533   9qcyxs
    2020-08-01 00:00:00+00:00   CISO     Los Angeles  ... -118.4168   9q5c3r
    2020-08-01 00:00:00+00:00   CISO          Fresno  ... -119.2567   9qe5q4
    2020-08-01 00:00:00+00:00   BANC      Stanislaus  ... -120.9314   9qdn04
    2020-08-01 00:00:00+00:00   BANC      Stanislaus  ... -120.9314   9qdn04
    ...                          ...             ...  ...       ...      ...
    2020-08-01 00:00:00+00:00   CISO          Orange  ... -117.9398   9qh0un
    2020-08-01 00:00:00+00:00   CISO       San Diego  ... -116.9106   9muc79
    2020-08-01 00:00:00+00:00   CISO          Solano  ... -121.9386   9qc63h
    2020-08-01 00:00:00+00:00   CISO  San Bernardino  ... -117.3556   9qh9ct
    2020-08-01 00:00:00+00:00   CISO          Tulare  ... -119.4302   9q7pfm

    [2690 rows x 15 columns]

To select the generators in Kern County CA in August 2020 run the following:

    Fleet("CA","Kern",2020,months=8)
"""

import logging
import numbers
import warnings

import pandas as pd
import numpy as np

from eia import Form860m
from geohash import geohash

class Fleet(pd.DataFrame):
    """Generation fleet data frame

    Index
    -----

    - `state`: state in which plant is located

    - `county`: county name

    - `geohash`: plant location geohash

    - `timestamp`: first day of the Form 860m month

    Columns
    -------

    - `region`: balance authority region name

    - `sector`: sector name

    - `id`: plant id

    - `unit`: unit id

    - `name`: plant name

    - `owner`: plant owner

    - `fuel`: plant energy source

    - `gen`: plant prime mover technology

    - `nameplate_MW`: nameplate capacity

    - `summer_MW`: summer capacity

    - `winter_MW`: winter capacity

    - `latitude`: plant location latitude

    - `longitude`: plant location longitude
    """

    COLUMNS = {
        "STATE": "state",
        "BA_CODE": "region",
        "COUNTY": "county",
        "SECTOR": "sector",
        "ID": "id",
        "GENERATOR_ID": "unit",
        "NAME": "name",
        "OWNER_NAME": "owner",
        "ENERGY_SOURCE_CODE": "fuel",
        "PRIME_MOVER_CODE": "gen",
        "NAMEPLATE_MW": "nameplate_MW",
        "SUMMER_MW": "summer_MW",
        "WINTER_MW": "winter_MW",
        "LAT": "latitude",
        "LON": "longitude",
        }

    def __init__(self,
        state:str|list[str]|None=None,
        county:str|list[str]|None=None,
        year:int|None=None,
        *,
        months:int|list[int]|None=None,
        ):
        """Generation fleet data frame constructor

        Arguments
        ---------

          - `state`: state(s) to include in data frame (`None` includes all
            states)

          - `county`: county name(s) to include in data frame (`None`
            includes all counties)

          - `year`: year from which to load data frame (required)

          - `months`: month(s) from which to load data frame (`None` loads
            all months)
        """

        # check year
        if year is None:
            raise TypeError("year is required")
        if not isinstance(year,numbers.Integral) or isinstance(year,bool):
            raise TypeError(f"{year=} is not an integer")
        year = int(year)

        # check months
        if months is None:
            months = range(1,13)
        elif isinstance(months,numbers.Integral):
            months = [months]
        else:
            months = [x for x in months]
        if not all(isinstance(x,numbers.Integral) and not isinstance(x,bool) for x in months):
            raise TypeError(f"{months=} contains non-integer values")
        months = [int(x) for x in months]
        if not all(1<=x<=12 for x in months):
            raise ValueError(f"{months=} contains invalid month value(s)")

        # check states and counties
        states = self._names(state,"state")
        counties = self._names(county,"county")

        # compile results
        result = []
        for month in months:

            # read Form 860m data for specified year/month
            data = Form860m(year=year,month=month,subset="Operating")

            # remove unwanted columns
            data.drop([x for x in data.columns if x not in self.COLUMNS],axis=1,inplace=True)

            # rename wanted columns
            data.rename(self.COLUMNS,axis=1,inplace=True)

            # set timestamp column
            data["timestamp"] = pd.to_datetime(f"{year}-{month:02d}-01 00:00:00+00:00")

            # append to results
            result.append(data.set_index("timestamp")[list(self.COLUMNS.values())].sort_index())

        # assemble results
        result = pd.concat(result).reset_index()

        # drop unwanted states and counties before the geohash calculation;
        # selecting by mask means missing values yield no rows instead of a
        # KeyError
        for column,values in {"state":states,"county":counties}.items():
            if values is None:
                continue
            missing = sorted(set(values) - set(result[column]))
            if missing:
                warnings.warn(f"no generators found for {column}(s) {', '.join(missing)}")
            result = result[result[column].isin(values)].copy()

        # set geohashes
        result["geohash"] = [
            None if pd.isna(lat) or pd.isna(lon) else geohash(lat,lon,6)
            for lat,lon in zip(result["latitude"],result["longitude"])]

        # set index
        result.set_index(["state","county","geohash","timestamp"],inplace=True)

        super().__init__(result)

    @staticmethod
    def _names(value:str|list[str]|None,name:str) -> list[str]|None:
        """@private Check a state or county argument and return it as a list"""
        if value is None:
            return None
        if isinstance(value,str):
            return [value]
        if not isinstance(value,list):
            raise TypeError(f"{name}={value!r} is not valid")
        if not all(isinstance(x,str) for x in value):
            raise TypeError(f"{name}={value!r} contains a non-string value")
        return value

    @classmethod
    def makeargs(cls,**kwargs) -> dict:
        """@private Return the kwargs accepted by this class constructor"""
        return {x:y for x,y in kwargs.items() if x in cls.__init__.__annotations__}

if __name__ == "__main__":

    # pd.options.display.width = None
    # pd.options.display.max_columns = None

    test = Fleet("CA",year=2020,months=8)
    print(test)
