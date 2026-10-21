"""Generation fleet data accessor

The `Generation` data frame collects generator fleet data from EIA Form 860m.

Example
-------

To select the generators in California in August 2020 run the following:

    from generator import Generator
    Generation(2020,8,states="CA")

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
    [Finished in 3.1s]
"""

import logging
import numbers
import warnings

import pandas as pd
import numpy as np

from eia import Form860m
from geohash import geohash

class Generation(pd.DataFrame):
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
        year:int,
        months:int|list[int]|None=None,
        states:str|list[str]|None=None,
        ):
        """Generation fleet data frame constructor

        Arguments
        ---------

          - `year`: year from which to load data frame

          - `month`: month(s) from which to load data frame

          - `state`: state(s) to include in data frame
        """

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

        # set geohashes
        result["geohash"] = [
            None if pd.isna(x.latitude) or pd.isna(x.longitude)
            else geohash(x.latitude,x.longitude,6)
            for _,x in result.iterrows()]

        # set index
        result.set_index(["state","county","geohash","timestamp"],inplace=True)

        # select desired state(s) (if any)
        if states is not None:
            if isinstance(states,str):
                states = [states]
            if not isinstance(states,list):
                raise TypeError(f"{states=} is not valid")
            if not all(isinstance(x,str) for x in states):
                raise TypeError(f"{states=} contain a non-string value")

            # warn about requested states that have no generators
            found = set(result.index.get_level_values("state"))
            missing = sorted(set(states) - found)
            if missing:
                warnings.warn(f"no generators found for state(s) {', '.join(missing)}")

            # select by mask so missing states yield no rows instead of a KeyError
            result = result[result.index.get_level_values("state").isin(states)]

        super().__init__(result)

if __name__ == "__main__":

    # pd.options.display.width = None
    # pd.options.display.max_columns = None

    test = Generation(2020,8,states="CA")
    print(test)
