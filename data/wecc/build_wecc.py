"""Build the WECC county hourly capacity and generation files

Writes one wide hourly file per generation category for the counties in the
Western Interconnection (WECC),

  - `capacity_{category}.csv.gz`: operating nameplate capacity in MW
  - `actual_{category}.csv.gz`: net generation in MW (= MWh in the hour)

with one row per UTC hour-beginning `timestamp` from 2018-01-01 00:00Z to
2022-12-31 23:00Z and one column per county named `"{county} {ST}"`
(e.g., `"Kern CA"`). Counties without a plant in a category are 0.

Syntax
------

    python data/wecc/build_wecc.py [--start YEAR] [--stop YEAR] [--output FOLDER]

Method
------

Plants are the Form 860m operating generators whose balancing authority is a
WECC balancing authority (`BAS`). Generators with no balancing authority are
included when they are in a state that is entirely in WECC (`STATES`).

Capacity is the sum of the nameplate MW of the operating generators in each
Form 860m month, held constant over the hours of that month.

Actual generation follows `generation.category.Category`: each plant's Form
923 monthly net generation by category is shaped into hours using the Form
930 hourly net generation of the plant's balancing authority for that
category (`generation.fuels.SHAPES`), with a flat shape where Form 930 data
is unavailable (always for January-June 2018), then summed by county.

Requirements
------------

Downloads EIA Forms 860m, 923 and 930 for 2018-2022; Form 930 for 2019 and
later needs an EIA API key (see `eudoxys/eia`).
"""

import os
import sys
import logging
import argparse
import warnings

import numpy as np
import pandas as pd

from eia import Form923
from generation.fleet import Fleet
from generation.fuels import CATEGORIES, SHAPES, category
from generation.category import hours, _shape, PRECISION

_logger = logging.getLogger(__file__)

BAS = [
    "AVA","AVRN","AZPS","BANC","BPAT","CHPD","CISO","DEAA","DOPD","EPE",
    "GCPD","GRID","GRIF","GRMA","GWA","HGMA","IID","IPCO","LDWP","NEVP",
    "NWMT","PACE","PACW","PGE","PNM","PSCO","PSEI","SCL","SRP","TEPC",
    "TIDC","TPWR","WACM","WALC","WAUW","WWA",
    ]
"""EIA Form 930 codes of the US balancing authorities in WECC"""

STATES = ["AZ","CA","ID","NV","OR","UT","WA"]
"""States entirely in WECC"""

def column(state:str,county:str) -> str:
    """Get the column name of a county"""
    return f"{county} {state}"

def plants(year:int,months:list[int]|None=None) -> pd.DataFrame:
    """Get the WECC operating generators of a year

    Returns one row per generator-month with columns `timestamp`, `state`,
    `county`, `ba`, `plant`, `category` and `nameplate_MW`.
    """
    data = []
    for month in months or range(1,13):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                fleet = Fleet(year=year,months=month).reset_index()
        except (ValueError,RuntimeError) as err:
            _logger.warning(f"Form 860m {year}-{month:02d} not available ({err})")
            continue
        data.append(fleet)
    if not data:
        raise RuntimeError(f"no Form 860m data for {year}")
    data = pd.concat(data,ignore_index=True)
    ba = data["region"].where(data["region"].notna(),"").astype(str).str.strip()
    wecc = ba.isin(BAS) | ((ba == "") & data["state"].isin(STATES))
    data = data.loc[wecc & data["county"].notna()].copy()
    data["ba"] = ba[data.index]
    data["category"] = [category(x,y) for x,y in zip(data["fuel"],data["gen"])]
    data["plant"] = data["id"].astype(int)
    data["county"] = data["county"].astype(str).str.strip()
    data["nameplate_MW"] = pd.to_numeric(data["nameplate_MW"],errors="coerce").fillna(0.0)
    return data[["timestamp","state","county","ba","plant","category","nameplate_MW"]]

def capacity(fleet:pd.DataFrame,year:int) -> dict[str,pd.DataFrame]:
    """Get the hourly county capacity of each category in a year"""
    index = hours(year)
    month = pd.Series(index.month,index=index)
    fleet = fleet.assign(
        column=[column(x,y) for x,y in zip(fleet["state"],fleet["county"])],
        month=pd.DatetimeIndex(fleet["timestamp"]).month,
        )
    available = sorted(fleet["month"].unique())
    result = {}
    for name in CATEGORIES:
        # months missing from Form 860m (not published) repeat the last
        # available month; a county with no generators in a month is 0
        monthly = (fleet.loc[fleet["category"] == name]
            .groupby(["month","column"])["nameplate_MW"].sum()
            .unstack("column").reindex(available).fillna(0.0)
            .reindex(range(1,13)).ffill().bfill().fillna(0.0))
        data = monthly.loc[month.values].set_axis(index,axis=0)
        data.columns.name = None
        result[name] = data
    return result

def actual(fleet:pd.DataFrame,year:int,refresh:bool=False) -> dict[str,pd.DataFrame]:
    """Get the hourly county net generation of each category in a year"""
    index = hours(year)
    position = {x:n for n,x in enumerate(index)}
    where = (fleet.drop_duplicates("plant",keep="last")
        .set_index("plant")[["state","county"]])
    where = {x:column(y["state"],y["county"]) for x,y in where.iterrows()}
    monthly = Form923(year,states=sorted(fleet["state"].unique()),
        by="plant",increments=False,refresh=refresh).reset_index()
    monthly["plant"] = monthly["plant"].astype(int)
    monthly = monthly.loc[monthly["plant"].isin(where)].copy()
    monthly["category"] = [category(x,y) for x,y in zip(monthly["fuel"],monthly["pm"])]
    monthly = (monthly.groupby(["category","plant","ba","timestamp"],dropna=False)["gen_mwh"]
        .sum().reset_index())
    result = {}
    for name in CATEGORIES:
        rows = monthly.loc[monthly["category"] == name]
        columns = {}
        for plant,ba,timestamp,energy in zip(rows["plant"],rows["ba"],rows["timestamp"],rows["gen_mwh"]):
            if pd.isna(energy) or energy == 0:
                continue
            shape = _shape(None if pd.isna(ba) else str(ba),year,
                pd.Timestamp(timestamp).month,SHAPES[name],refresh)
            values = columns.setdefault(where[plant],np.zeros(len(index)))
            start = position[shape.index[0]]
            values[start:start+len(shape)] += energy * shape.values
        result[name] = pd.DataFrame(columns,index=index)
    return result

def build(start:int=2018,stop:int=2022,output:str=".",refresh:bool=False) -> dict[str,str]:
    """Build the WECC capacity and actual generation files

    Arguments
    ---------

      - `start`: first year

      - `stop`: last year (inclusive)

      - `output`: output folder

      - `refresh`: refresh cached EIA data

    Returns
    -------

      - `dict`: file pathname by `"{kind}_{category}"`
    """
    parts = {f"{x}_{y}":[] for x in ("capacity","actual") for y in CATEGORIES}
    for year in range(start,stop+1):
        _logger.info(f"building {year}")
        fleet = plants(year)
        for kind,data in (("capacity",capacity(fleet,year)),("actual",actual(fleet,year,refresh))):
            for name,frame in data.items():
                parts[f"{kind}_{name}"].append(frame)

    # every file has the same columns: all WECC counties with a plant in any year
    counties = sorted({x for frames in parts.values() for frame in frames for x in frame.columns},
        key=lambda x:(x.rsplit(" ",1)[1],x))
    os.makedirs(output,exist_ok=True)
    result = {}
    for name,frames in parts.items():
        data = (pd.concat([x.reindex(columns=counties) for x in frames])
            .fillna(0.0).round(PRECISION))
        data.index.name = "timestamp"
        pathname = os.path.join(output,f"{name}.csv.gz")
        data.to_csv(pathname,index=True,header=True,compression="gzip",
            date_format="%Y-%m-%d %H:%M:%S+00:00")
        _logger.info(f"saved {pathname} {data.shape}")
        result[name] = pathname
    return result

def main(argv:list[str]|None=None) -> int:
    """Command line entry point"""
    parser = argparse.ArgumentParser(description=__doc__.split("\n",1)[0])
    parser.add_argument("--start",type=int,default=2018,help="first year")
    parser.add_argument("--stop",type=int,default=2022,help="last year (inclusive)")
    parser.add_argument("--output",default=os.path.dirname(os.path.abspath(__file__)),
        help="output folder")
    parser.add_argument("--refresh",action="store_true",help="refresh cached EIA data")
    parser.add_argument("--verbose",action="store_true",help="log progress")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING)
    build(args.start,args.stop,args.output,args.refresh)
    return 0

if __name__ == "__main__":
    sys.exit(main())
