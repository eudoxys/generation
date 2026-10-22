"""Syntax
------

    generation YEAR [MONTH[,MONTH[,...]]] [STATE[,STATE[,...]]]
        [-C|--county COUNTY[,COUNTY[,...]]] [-D|--dataset DATASET]
        [-o|--output FILE] [-f|--format {csv,gzip}] [-r|--refresh]
        [-h|--help] [-w|--warning] [-d|--debug]

The `DATASET` is one of the following:

  - `fleet`: generator inventory (`generation.fleet.Fleet`, the default)

  - `total`: total hourly generation (`generation.total.Total`)

  - `dispatchable`: dispatchable hourly generation
    (`generation.dispatchable.Dispatchable`)

  - `nondispatchable`: non-dispatchable hourly generation
    (`generation.nondispatchable.Nondispatchable`)

  - `coal`, `natural_gas`, `oil`, `nuclear`, `hydro`, `geothermal`,
    `biomass`, `battery_storage`, `pumped_storage`, `other`, `solar`, `wind`:
    hourly generation of one category (e.g., `generation.coal.Coal`)

The hourly datasets require exactly one `STATE` and one `COUNTY`. For these
datasets `MONTH` selects the hours output.

Examples
--------

To download the generation data for California in August 2020 run the command


    generation 2020 8 CA

which outputs the following

                                    region          county              sector     id   unit  ... summer_MW winter_MW   latitude longitude  geohash
    state timestamp                                                                           ...                                                  
    CA    2020-08-01 00:00:00+00:00   CISO          Placer         IPP Non-CHP     34     1P  ...      12.1      12.1  39.134259 -120.9533   9qcyxs
          2020-08-01 00:00:00+00:00   CISO     Los Angeles    Electric Utility     72      1  ...      10.1      10.1  34.011350 -118.4168   9q5c3r
          2020-08-01 00:00:00+00:00   CISO          Fresno    Electric Utility    104      1  ...      95.0      95.0  37.147926 -119.2567   9qe5q4
          2020-08-01 00:00:00+00:00   BANC      Stanislaus    Electric Utility    151      1  ...      53.5      53.5  37.629360 -120.9314   9qdn04
          2020-08-01 00:00:00+00:00   BANC      Stanislaus    Electric Utility    151      2  ...      53.5      53.5  37.629360 -120.9314   9qdn04
    ...                                ...             ...                 ...    ...    ...  ...       ...       ...        ...       ...      ...
          2020-08-01 00:00:00+00:00   CISO          Orange  Industrial Non-CHP  63758  KROLH  ...       1.2       1.2  33.917918 -117.9398   9qh0un
          2020-08-01 00:00:00+00:00   CISO       San Diego         IPP Non-CHP  63834  GTWAY  ...     250.0     250.0  32.570556 -116.9106   9muc79
          2020-08-01 00:00:00+00:00   CISO          Solano  Commercial Non-CHP  63928   6701  ...       1.4       0.7  38.388670 -121.9386   9qc63h
          2020-08-01 00:00:00+00:00   CISO  San Bernardino         IPP Non-CHP  63986  10136  ...       0.9       0.9  34.090318 -117.3556   9qh9ct
          2020-08-01 00:00:00+00:00   CISO          Tulare         IPP Non-CHP  63993  FTF02  ...       1.0       1.0  36.546901 -119.4302   9q7pfm

    [2690 rows x 15 columns]

To save the 2020 hourly total generation of Kern County CA run the command

    generation 2020 CA -C Kern -D total -o kern_2020.csv
"""

import os
import sys
import argparse
import gzip
import warnings
import logging

import pandas as pd

from generation.fleet import Fleet
from generation.total import Total
from generation.dispatchable import Dispatchable
from generation.nondispatchable import Nondispatchable
from generation.coal import Coal
from generation.natural_gas import NaturalGas
from generation.oil import Oil
from generation.nuclear import Nuclear
from generation.hydro import Hydro
from generation.geothermal import Geothermal
from generation.biomass import Biomass
from generation.battery_storage import BatteryStorage
from generation.pumped_storage import PumpedStorage
from generation.other import Other
from generation.solar import Solar
from generation.wind import Wind

DATASETS = {
    "fleet": Fleet,
    "total": Total,
    "dispatchable": Dispatchable,
    "nondispatchable": Nondispatchable,
    "coal": Coal,
    "natural_gas": NaturalGas,
    "oil": Oil,
    "nuclear": Nuclear,
    "hydro": Hydro,
    "geothermal": Geothermal,
    "biomass": Biomass,
    "battery_storage": BatteryStorage,
    "pumped_storage": PumpedStorage,
    "other": Other,
    "solar": Solar,
    "wind": Wind,
    }
"""Datasets available from the command line"""

E_OK = 0
"""Exit code on success"""

E_FAILED = 1
"""Exit code on failure"""

E_SYNTAX = 2
"""Exit code on syntax error"""

def _months(text:str) -> list[int]:
    """Parse a comma-separated list of months"""
    try:
        months = [int(x) for x in text.split(",")]
    except ValueError as err:
        raise argparse.ArgumentTypeError(
            f"{text!r} is not a comma-separated list of months") from err
    if not all(1 <= x <= 12 for x in months):
        raise argparse.ArgumentTypeError(f"{text!r} contains a month outside 1-12")
    return months

def main(
    *args:str,
    **kwargs:str,
    ) -> int:
    """Generation data accessor command line processor

    Arguments
    ---------

      - `*args`: command line arguments (none reverts to `sys.argv`)

      - `**kwargs`: options, passed as `--name=value`

    Returns
    -------

      - `int`: return/exit code
    """
    try:

        # support direct call to main
        argv = list(args) if args or kwargs else sys.argv[1:]
        argv += [f"--{x}={y}" for x,y in kwargs.items()]

        # setup command line parser
        parser = argparse.ArgumentParser(
            prog="generation",
            description="Electric generation data accessor",
            epilog="See https://www.eudoxys.com/generation for documentation.",
            )

        parser.add_argument("year",
            type=int,
            help="year for which to download generation data")

        parser.add_argument("month",
            nargs="?",
            default=None,
            type=str,
            help="(comma separated) month(s) for which to download generation data")

        parser.add_argument("states",
            nargs="?",
            default=None,
            type=str,
            help="(comma separated) state(s) for which to download generation data")

        parser.add_argument("-C","--county",
            default=None,
            type=str,
            help="(comma separated) county name(s) for which to download generation data")

        parser.add_argument("-D","--dataset",
            default="fleet",
            choices=list(DATASETS),
            help="dataset to output (default fleet)")

        parser.add_argument("-r","--refresh",
            action="store_true",
            help="refresh cached data")

        parser.add_argument("-o","--output",
            default=None,
            help="set output file name")

        parser.add_argument("-f","--format",
            default=None,
            choices=["csv","gzip"],
            help="specify output format (depends on command)")

        parser.add_argument("-w","--warning",
            action="store_true",
            help="enable warning messages from python")

        parser.add_argument("-d","--debug",
            action="store_true",
            help="enable debug traceback on exceptions")

        # parse arguments
        args = parser.parse_args(argv)

        # allow the month to be omitted when states are given
        if args.month is not None and not args.month.replace(",","").isdigit():
            if args.states is not None:
                raise ValueError(f"month={args.month!r} is not valid")
            args.states,args.month = args.month,None
        if args.month is not None:
            args.month = _months(args.month)

        # setup warning handling
        if not args.warning:
            warnings.showwarning = lambda *x:print(
                f"WARNING [{__package__}]:",
                x[0],
                flush=True,
                file=sys.stderr,
                )

        # enable debug output
        if args.debug:
            logging.basicConfig(level=logging.DEBUG)

        # get data
        states = args.states.split(",") if args.states else None
        counties = args.county.split(",") if args.county else None
        if args.dataset == "fleet":
            data = Fleet(states,counties,args.year,months=args.month)
        else:
            if not states or len(states) != 1 or not counties or len(counties) != 1:
                raise ValueError(f"dataset={args.dataset} requires one state and one county")
            data = DATASETS[args.dataset](states[0],counties[0],args.year,refresh=args.refresh)
            if args.month:
                data = data.loc[data.index.month.isin(args.month)]

        # output data
        if args.output is None:
            if args.format is None:
                print(data)
            elif args.format == "csv":
                print(data.to_csv(index=True,header=True))
            elif args.format == "gzip":
                sys.stdout.flush()
                sys.stdout.buffer.write(
                    gzip.compress(data.to_csv(index=True,header=True).encode()))
                sys.stdout.buffer.flush()
        else:
            if args.output.endswith(".csv.gz"):
                ext = "gzip"
            elif args.output.endswith(".csv"):
                ext = "csv"
            else:
                ext = None
            if args.format and ext and args.format != ext:
                raise ValueError(f"format={args.format} conflicts with output={args.output}")
            fmt = args.format or ext
            if fmt is None:
                raise ValueError(f"output={args.output} is not valid (use .csv, .csv.gz, or --format)")
            data.to_csv(args.output,index=True,header=True,
                compression="gzip" if fmt == "gzip" else None)

        return E_OK

    # pylint: disable=broad-exception-caught
    except Exception as err:

        if getattr(args,"debug",False):
            raise

        print(f"ERROR [generation]: {err}",file=sys.stderr)
        return E_FAILED

if __name__ == "__main__":

    sys.exit(main())
