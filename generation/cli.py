"""Syntax
------

    generator YEAR [MONTH[,MONTH[,...]]] [STATE[,STATE[,...]]]
        [-h|--help] [-w|--warning] [-d|--debug]

Examples
--------

To download the generation data for California in August 2020 run the command


    generator 2020 8 CA

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
"""

import os
import sys
import argparse
import warnings
import logging

import pandas as pd

from generation.generation import Generation

E_OK = 0
"""Exit code on success"""

E_FAILED = 1
"""Exit code on failure"""

E_SYNTAX = 2
"""Exit code on syntax error"""

def main(
    *args:list[str],
    **kwargs:[dict[str,str]],
    ) -> int:
    """Generator data accessor command line processor

    Arguments
    ---------

      - `*args`: command line arguments (`None` reverts to `sys.argv`)

    Returns
    -------

      - `int`: return/exit code
    """
    try:

        # support direct call to main
        if args:
            sys.argv = [__file__] + list(args)
        if kwargs:
            sys.argv += [f"--{x}={y}" for x,y in kwargs.items()]

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
            default=None,
            type=int,
            help="month for which to download generation data")

        parser.add_argument("states",
            default=None,
            type=str,
            help="(comma separated) state(s) for which to download generation data")

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
        args = parser.parse_args()

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
            logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)

        # get data
        data = Generation(
            year=args.year,
            months=args.month,
            states=args.states.split(","),
            )

        # output data
        if args.output is None:
            if args.format is None:
                print(data)
            elif args.format == "csv":
                print(data.to_csv(index=True,header=True))
        elif args.output.endswith(".csv"):
            data.to_csv(args.output,index=True,header=True)
        elif args.output.endswith(".csv.gz"):
            data.to_csv(args.output,compression="gzip",index=True,header=True)
        else:
            raise ValueError(f"output={args.output} is not valid")

        return E_OK

    # pylint: disable=broad-exception-caught
    except Exception as err:

        if getattr(args,"debug"):
            raise

        print(f"ERROR [generation]: {err}",file=sys.stderr)
        return E_FAILED

if __name__ == "__main__":

    main("plot","-d",state="CA",county="Alameda",year=2020,dataset="total")
