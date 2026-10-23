# generation

Generation fleet data accessor.

`generation` loads the US generator inventory from the EIA Form 860m monthly
archive (via [eia](https://github.com/eudoxys/eia)) and returns it as a pandas
data frame of operating units, with plant location, capacity, fuel and prime
mover, and a 6-character [geohash](https://github.com/eudoxys/geohash) for
each plant.

## Installation

```
pip install git+https://github.com/eudoxys/generation
```

## Command line

```
generation YEAR [MONTH[,MONTH[,...]]] [STATE[,STATE[,...]]]
    [-o|--output FILE] [-f|--format {csv,gzip}]
    [-h|--help] [-w|--warning] [-d|--debug]
```

For example, to save the California fleet for August 2020 as a CSV file:

```
generation 2020 8 CA -o ca_2020_08.csv
```

Output files ending in `.csv.gz` are written gzip-compressed.

## Python

```python
from generation import Generation

fleet = Generation(2020, 8, states=["CA"])
fleet.groupby("fuel")["nameplate_MW"].sum()
```

## Data

Each row is one operating generating unit in the given month.

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

## Acknowledgments

- This material is based on work supported by the U.S. Department of Energy’s Office of Electricity through a grant from the Grid Controls and Communications Division
