# generation

Generation fleet data accessor.

`generation` loads the US generator inventory from the EIA Form 860m monthly
archive (via [eia](https://github.com/eudoxys/eia)) and returns it as a pandas
data frame of operating units, with plant location, capacity, fuel and prime
mover, and a 6-character [geohash](https://github.com/eudoxys/geohash) for
each plant.

It also estimates the hourly net generation of each county by energy source
category, by shaping EIA Form 923 monthly plant net generation with the EIA
Form 930 hourly generation of the plant's balancing authority.

## Installation

```
pip install git+https://github.com/eudoxys/generation
```

## Command line

```
generation YEAR [MONTH[,MONTH[,...]]] [STATE[,STATE[,...]]]
    [-C|--county COUNTY[,COUNTY[,...]]] [-D|--dataset DATASET]
    [-o|--output FILE] [-f|--format {csv,gzip}] [-r|--refresh]
    [-h|--help] [-w|--warning] [-d|--debug]
```

`DATASET` is `fleet` (the default), `total`, `dispatchable`,
`nondispatchable`, or one of the 12 categories listed below. The hourly
datasets need exactly one state and one county.

For example, to save the California fleet for August 2020 as a CSV file:

```
generation 2020 8 CA -o ca_2020_08.csv
```

To save the 2020 hourly total generation of Kern County CA:

```
generation 2020 CA -C Kern -D total -o kern_2020.csv
```

Output files ending in `.csv.gz` are written gzip-compressed.

## Python

```python
from generation import Fleet, Total, Wind

fleet = Fleet("CA", year=2020, months=8)
fleet.groupby("fuel")["nameplate_MW"].sum()

total = Total("CA", "Kern", 2020)    # hourly MW by category
wind = Wind("CA", "Kern", 2020)      # hourly MW by wind plant
```

All the hourly data frames are constructed as `Class(state,county,year)`.

| Module | Class | Columns |
|---|---|---|
| `coal`, `natural_gas`, `oil`, `nuclear`, `hydro`, `geothermal`, `biomass`, `battery_storage`, `pumped_storage`, `other` | `Coal`, `NaturalGas`, `Oil`, `Nuclear`, `Hydro`, `Geothermal`, `Biomass`, `BatteryStorage`, `PumpedStorage`, `Other` | `plant_{id}_MW` per plant, `{category}_MW` |
| `solar`, `wind` | `Solar`, `Wind` | `plant_{id}_MW` per plant, `{category}_MW` |
| `dispatchable` | `Dispatchable` | 10 dispatchable `{category}_MW`, `dispatchable_MW` |
| `nondispatchable` | `Nondispatchable` | `solar_MW`, `wind_MW`, `nondispatchable_MW` |
| `total` | `Total` | all of the above, `total_MW` |

Form 930 hourly data requires an EIA API key in `~/.eia/api_key` or
`EIA_API_KEY`. Without it, or before July 2018, monthly energy is spread
evenly over the hours of the month.

## Reviewing generation data

The marimo notebook `generation/_review/review_generation_marimo.py` shows the
`Total` data of a county as hourly, monthly and daily-profile plots with
summary statistics. Run it with

```
marimo edit generation/_review/review_generation_marimo.py
```

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

## Documentation

Full documentation is at https://www.eudoxys.com/generation.

## License

MIT. See [LICENSE](LICENSE).
Generation fleet data accessor

## Design

See [DESIGN.md](DESIGN.md) for the package design: hourly, county-level
(geohash) net generation by fuel, split into dispatchable/non-dispatchable
and AGC/non-AGC generation, from January 2018.
