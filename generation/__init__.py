"""Generation fleet data accessor

Syntax
------

    generation YEAR [MONTH[,MONTH[,...]]] [STATE[,STATE[,...]]]
        [-C|--county COUNTY[,COUNTY[,...]]] [-D|--dataset DATASET]
        [-o|--output FILE] [-f|--format {csv,gzip}] [-r|--refresh]
        [-h|--help] [-w|--warning] [-d|--debug] [--version]

Positional arguments
--------------------

  - `YEAR`: year of the data

  - `MONTH`: (comma separated) month(s); for hourly datasets, selects the
    hours output

  - `STATE`: (comma separated) state code(s); hourly datasets need exactly one

Optional arguments
------------------

  - `-C|--county`: (comma separated) county name(s); hourly datasets need
    exactly one

  - `-D|--dataset`: `fleet` (default), `total`, `dispatchable`,
    `nondispatchable`, or one of the 12 categories (see `generation.cli`)

  - `-d|--debug`: enable debug logging and traceback on exceptions

  - `-f|--format`: output format, `csv` or `gzip`

  - `-h|--help`: show the help message and exit

  - `-o|--output`: output file name (`.csv` or `.csv.gz`)

  - `-r|--refresh`: rebuild cached category data

  - `-w|--warning`: enable warning messages from python

  - `--version`: show the package version and exit

Description
-----------

Hourly, county-level models of US utility-scale generation assembled from
EIA public data. See `DESIGN.md` in the source repository for the package
design.

Given a state, a county and a year, each generation data frame
`Class(state,county,year)` (e.g., `generation.total.Total`) returns a frame
that is expected to satisfy:

  1. **Shape.** One row per UTC hour-beginning `timestamp` of the year (8760
     or 8784 rows); the index is named `timestamp` and is tz-aware UTC.

  2. **Columns.** A `Category` frame has one `plant_{id}_MW` column per
     contributing plant and a `{category}_MW` total; a `Combination` frame
     keeps the total column of each category it combines and adds its own
     total (`dispatchable_MW`, `nondispatchable_MW`, `total_MW`).

  3. **Totals.** Each total column equals the sum of the columns it
     combines, and the plant columns of a category sum, over each month, to
     the plants' Form 923 monthly net generation.

  4. **Repeatability.** Category frames are cached with `eudoxys/cache`; a
     cached frame is returned unchanged unless `refresh=True`.

`generation.fleet.Fleet` returns the Form 860m operating generator
inventory (one row per unit and month) used to find the plants in a county.

What is not promised
--------------------

  - CEMS hourly unit loads, NRC reactor status, and the January-June 2018
    backfill are not implemented yet; those hours use a flat monthly shape.

  - Form 930 hourly shapes need an EIA API key; without one all categories
    use a flat monthly shape.

  - EIA state-fuel increments (Form 923 plant `99999`) are not located in a
    county and are not included.

  - AGC flags, county geohash keys and the long `county_generation` output
    table described in `DESIGN.md` are not implemented yet.

  - Results have not been validated against independent hourly data.

Data
----

  - `plant_{id}_MW`: hourly mean net generation of plant `id` (MW, equal to
    MWh in the hour); can be negative.

  - `{category}_MW`: hourly net generation of a category in the county (MW).

  - `dispatchable_MW`, `nondispatchable_MW`, `total_MW`: combined net
    generation (MW).

```mermaid
flowchart LR
    F860M[(Form 860m)] --> Fleet --> Category
    F923[(Form 923)] --> Category
    F930[(Form 930)] --> Category
    Category --> Dispatchable --> Total
    Category --> Nondispatchable --> Total
```

Modules
-------

- `generation.cli`: Command line interface

- `generation.fleet`: Generator fleet inventory (EIA Form 860m)

- `generation.fuels`: Energy source codes and generation categories

- `generation.category`: Generation data frame base classes and method

- `generation.total`: Total generation (dispatchable and non-dispatchable)

- `generation.dispatchable`: Dispatchable generation

  - `generation.coal`: Coal generation

  - `generation.natural_gas`: Natural gas generation

  - `generation.oil`: Oil generation

  - `generation.nuclear`: Nuclear generation

  - `generation.hydro`: Conventional hydroelectric generation

  - `generation.geothermal`: Geothermal generation

  - `generation.biomass`: Biomass generation

  - `generation.battery_storage`: Battery storage net generation

  - `generation.pumped_storage`: Pumped storage net generation

  - `generation.other`: Other generation

- `generation.nondispatchable`: Non-dispatchable generation

  - `generation.solar`: Utility-scale solar generation

  - `generation.wind`: Wind generation

Package information
-------------------

  - Source code: https://github.com/eudoxys/generation

  - Documentation: https://www.eudoxys.com/generation

  - Issues: https://github.com/eudoxys/generation/issues

  - License: https://github.com/eudoxys/generation/blob/main/LICENSE

  - Dependencies: 

    - [pandas](https://pypi.org/project/pandas/)
    - [eia](https://github.com/eudoxys/eia/)
    - [cache](https://github.com/eudoxys/cache/)
    - [geohash](https://github.com/eudoxys/geohash/)
    - [numpy](https://pypi.org/project/numpy/)
"""

try:
    import importlib.metadata
    __version__ = importlib.metadata.version("generation")
except Exception: # pylint: disable=broad-exception-caught
    __version__ = "dev"

# re-export the public API
from generation.fleet import Fleet
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
from generation.dispatchable import Dispatchable
from generation.nondispatchable import Nondispatchable
from generation.total import Total
from generation.cli import main
