[![Validation](https://github.com/eudoxys/generation/actions/workflows/validate.yaml/badge.svg)](https://github.com/eudoxys/generation/actions/workflows/validate.yaml)
[![Documentation](https://github.com/eudoxys/generation/actions/workflows/deploy-pages.yaml/badge.svg)](https://github.com/eudoxys/generation/actions/workflows/deploy-pages.yaml)

Generation fleet data accessor

`generation` produces hourly, county-level estimates of US utility-scale net
generation by energy source category, for modelers who need generation time
series that line up with [loads](https://github.com/eudoxys/loads). It loads
the generator inventory from the EIA Form 860m monthly archive (via
[eia](https://github.com/eudoxys/eia)), assigns each plant's EIA Form 923
monthly net generation to one of 12 categories, and shapes it into hours with
the EIA Form 930 hourly generation of the plant's balancing authority. The
categories are combined into dispatchable, non-dispatchable and total
generation. See [DESIGN.md](DESIGN.md) for the package design.

# Documentation

See https://www.eudoxys.com/generation

# Installation

Install using Eudoxys Package Manager:

    pip install --upgrade eudoxys
    epm install generation

Install using `pip`:

    pip install git+https://github.com/eudoxys/generation

Form 930 hourly data requires an EIA API key in `~/.eia/api_key` or
`EIA_API_KEY`. Without it, or before July 2018, monthly energy is spread
evenly over the hours of the month.

# Maintenance

## Update docs

    make docs

## Run tests

    pip install -e . pytest
    pytest

The tests run offline against small fake EIA tables and take a few seconds.
See [`generation/_test/README.md`](generation/_test/README.md).

## Cache build

Category frames are cached with [cache](https://github.com/eudoxys/cache)
under `generation/0/`. Use `-r|--refresh` on the command line, or
`refresh=True` in Python, to rebuild a county-year.

## Reviewing generation data

The marimo notebook `generation/_review/review_generation_marimo.py` shows the
`Total` data of a county as hourly, monthly and daily-profile plots with
summary statistics. See [`generation/_review/README.md`](generation/_review/README.md).

# Examples

## Command line

    generation YEAR [MONTH[,MONTH[,...]]] [STATE[,STATE[,...]]]
        [-C|--county COUNTY[,COUNTY[,...]]] [-D|--dataset DATASET]
        [-o|--output FILE] [-f|--format {csv,gzip}] [-r|--refresh]
        [-h|--help] [-w|--warning] [-d|--debug] [--version]

`DATASET` is `fleet` (the default), `total`, `dispatchable`,
`nondispatchable`, or one of the 12 categories listed below. The hourly
datasets need exactly one state and one county.

To save the California fleet for August 2020 as a CSV file:

    generation 2020 8 CA -o ca_2020_08.csv

To save the 2020 hourly total generation of Kern County CA:

    generation 2020 CA -C Kern -D total -o kern_2020.csv

Output files ending in `.csv.gz` are written gzip-compressed.

## Python

    from generation import Fleet, Total, Wind

    fleet = Fleet("CA", year=2020, months=8)
    fleet.groupby("fuel")["nameplate_MW"].sum()

    total = Total("CA", "Kern", 2020)    # hourly MW by category
    wind = Wind("CA", "Kern", 2020)      # hourly MW by wind plant

All the hourly data frames are constructed as `Class(state,county,year)`.

| Module | Class | Columns |
|---|---|---|
| `coal`, `natural_gas`, `oil`, `nuclear`, `hydro`, `geothermal`, `biomass`, `battery_storage`, `pumped_storage`, `other` | `Coal`, `NaturalGas`, `Oil`, `Nuclear`, `Hydro`, `Geothermal`, `Biomass`, `BatteryStorage`, `PumpedStorage`, `Other` | `plant_{id}_MW` per plant, `{category}_MW` |
| `solar`, `wind` | `Solar`, `Wind` | `plant_{id}_MW` per plant, `{category}_MW` |
| `dispatchable` | `Dispatchable` | 10 dispatchable `{category}_MW`, `dispatchable_MW` |
| `nondispatchable` | `Nondispatchable` | `solar_MW`, `wind_MW`, `nondispatchable_MW` |
| `total` | `Total` | all of the above, `total_MW` |

## Fleet data

Each row of `Fleet` is one operating generating unit in the given month.

| Column | Description |
|---|---|
| `state` | State in which the plant is located |
| `timestamp` | First day of the Form 860m month |
| `region` | Balancing authority code |
| `county` | County name |
| `sector` | Sector name |
| `id` | EIA plant id |
| `unit` | Generator id |
| `name` | Plant name |
| `owner` | Owner name |
| `fuel` | Energy source code |
| `gen` | Prime mover code |
| `nameplate_MW` | Nameplate capacity |
| `summer_MW` | Net summer capacity |
| `winter_MW` | Net winter capacity |
| `latitude`, `longitude` | Plant location |
| `geohash` | Plant location geohash (6 characters) |

## Repository data

The curated data in the repository's `data/` folder (e.g., the BPA and WAPA
hydro data in `data/hydro/`) is not installed with the package. `Data`
downloads a file from the repository the first time it is used, caches it,
and returns it as a data frame:

```python
from generation import Data
dams = Data("hydro/BPA_dams/dam_list.csv")
```

Keyword arguments other than `refresh` are passed to `pandas.read_csv()`.

# License

MIT. See [LICENSE](LICENSE) and [COPYRIGHT.md](COPYRIGHT.md).

# Acknowledgments

- This material is based on work supported by the U.S. Department of Energy’s Office of Electricity through a grant from the Grid Controls and Communications Division
