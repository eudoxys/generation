"""Build the WECC 240 node hourly capacity and generation files

Aggregates the WECC county files made by `build_wecc.py`,

  - `capacity_{category}.csv.gz`: operating nameplate capacity in MW
  - `actual_{category}.csv.gz`: net generation in MW (= MWh in the hour)

to the generation nodes of the WECC 240 bus model (`eudoxys/wecc240`),
writing

  - `node_capacity_{category}.csv.gz`
  - `node_actual_{category}.csv.gz`

with the same `timestamp` rows and one column per node geohash (e.g.,
`9q4gcx`), sorted.

Syntax
------

    python data/wecc/build_nodes.py [--input FOLDER] [--output FOLDER]
        [--mapping CSV] [--verbose]

Method
------

Each county is mapped to a node by the `gen` column of the `wecc240`
county-to-node map `county_node_map.csv` (`MAPPING`), which gives the
nearest generation node of each WECC county. The map is read as weights
$w_{cn}$ (here 1 for the county's node and 0 otherwise), and each node's
value is

$$ x_n(t) = \\sum_c w_{cn} x_c(t) $$

so every hour's total over the mapped counties is kept.

County columns are matched to the map by name (`"{county} {ST}"`). Names
that Form 860m spells differently from the map are corrected by `ALIASES`.
A county that is still not in the map (e.g., a county outside the WECC 240
footprint) is left out, and a warning gives the energy and peak capacity
that are dropped.

Requirements
------------

Reads `county_node_map.csv` from the `eudoxys/wecc240` GitHub repository
unless `--mapping` names a local copy. Needs the county files built by
`build_wecc.py` in `--input`.
"""

import os
import sys
import logging
import argparse

import pandas as pd

from generation.fuels import CATEGORIES
from generation.category import PRECISION

_logger = logging.getLogger(__file__)

MAPPING = "https://raw.githubusercontent.com/eudoxys/wecc240/main/wecc240/data/county_node_map.csv"
"""URL of the `wecc240` county-to-node map"""

ALIASES = {
    "Dona Ana NM":"Doña Ana NM",
    "Sacremento CA":"Sacramento CA",
    "Oceanside CA":"San Diego CA",
    }
"""County column names corrected to the `wecc240` map spelling (Form 860m
misspellings, and a city given as the county)"""

KINDS = ["capacity","actual"]
"""Kinds of county file aggregated"""

def weights(mapping:str=MAPPING) -> pd.DataFrame:
    """Get the county-to-node weights

    Arguments
    ---------

      - `mapping`: pathname or URL of `county_node_map.csv`

    Returns
    -------

      - `pandas.DataFrame`: weights with one row per county (`county_st`)
        and one column per generation node geohash, sorted; each row sums
        to 1
    """
    data = pd.read_csv(mapping,usecols=["county_st","gen"]).dropna()
    if data["county_st"].duplicated().any():
        raise ValueError(f"{mapping} has duplicate counties")
    result = (pd.crosstab(data["county_st"],data["gen"])
        .astype(float).sort_index(axis=1))
    result.index.name = "county_st"
    result.columns.name = None
    return result

def aggregate(data:pd.DataFrame,weight:pd.DataFrame,name:str="") -> pd.DataFrame:
    """Aggregate county columns to nodes

    Arguments
    ---------

      - `data`: hourly frame with one column per county

      - `weight`: county-to-node weights (see `weights`)

      - `name`: name of the data used in warnings

    Returns
    -------

      - `pandas.DataFrame`: hourly frame with one column per node in
        `weight`
    """
    data = data.rename(columns=ALIASES)
    data = data.T.groupby(level=0).sum().T  # an alias may repeat a county
    missing = [x for x in data.columns if x not in weight.index and (data[x] != 0).any()]
    if missing:
        dropped = data[missing].sum(axis=1)
        energy = f", {dropped.sum()/1000:.1f} GWh" if name.startswith("actual") else ""
        _logger.warning(f"{name or 'data'}: {len(missing)} counties not in the "
            f"node map are dropped ({', '.join(missing)}): "
            f"peak {dropped.abs().max():.1f} MW{energy}")
    counties = [x for x in data.columns if x in weight.index]
    result = data[counties].fillna(0.0) @ weight.loc[counties]
    result.index.name = data.index.name
    return result.round(PRECISION)

def build(input:str=".",output:str=".",mapping:str=MAPPING) -> dict[str,str]: # pylint: disable=redefined-builtin
    """Build the WECC 240 node capacity and actual generation files

    Arguments
    ---------

      - `input`: folder of the county files made by `build_wecc.py`

      - `output`: output folder

      - `mapping`: pathname or URL of `county_node_map.csv`

    Returns
    -------

      - `dict`: file pathname by `"{kind}_{category}"`
    """
    weight = weights(mapping)
    os.makedirs(output,exist_ok=True)
    result = {}
    for kind in KINDS:
        for category in CATEGORIES:
            name = f"{kind}_{category}"
            source = os.path.join(input,f"{name}.csv.gz")
            data = pd.read_csv(source,index_col="timestamp")
            nodes = aggregate(data,weight,name)
            pathname = os.path.join(output,f"node_{name}.csv.gz")
            nodes.to_csv(pathname,index=True,header=True,compression="gzip")
            _logger.info(f"saved {pathname} {nodes.shape}")
            result[name] = pathname
    return result

def main(argv:list[str]|None=None) -> int:
    """Command line entry point"""
    folder = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(description=__doc__.split("\n",1)[0])
    parser.add_argument("--input",default=folder,help="folder of the county files")
    parser.add_argument("--output",default=folder,help="output folder")
    parser.add_argument("--mapping",default=MAPPING,help="pathname or URL of county_node_map.csv")
    parser.add_argument("--verbose",action="store_true",help="log progress")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING)
    build(args.input,args.output,args.mapping)
    return 0

if __name__ == "__main__":
    sys.exit(main())
