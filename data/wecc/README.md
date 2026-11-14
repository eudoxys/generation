# WECC county hourly generation capacity and net generation (2018–2022)

Hourly, county-level operating capacity and net generation of US
utility-scale generators in the Western Interconnection (WECC), one file per
generation category, built by `build_wecc.py` from EIA Forms 860m, 923 and
930 using the `generation` package method.

These files are not installed with the `generation` package. Read them with
`generation.data.Data`, e.g.,

```python
from generation import Data
solar = Data("wecc/actual_solar.csv.gz",index_col="timestamp",parse_dates=True)
```

## Files

| File | Content |
|---|---|
| `capacity_{category}.csv.gz` | operating nameplate capacity, MW |
| `actual_{category}.csv.gz` | net generation, MW (hourly mean MW = MWh in the hour) |
| `build_wecc.py` | script that builds the files |
| `node_capacity_{category}.csv.gz` | capacity aggregated to WECC 240 generation nodes, MW (built by `build_nodes.py`) |
| `node_actual_{category}.csv.gz` | net generation aggregated to WECC 240 generation nodes, MW (built by `build_nodes.py`) |
| `build_nodes.py` | script that aggregates the county files to WECC 240 nodes |
| `review_node_data.py` | marimo notebook to review the node files by state or WECC 240 area, year and month |

`{category}` is one of the 12 categories in `generation.fuels.CATEGORIES`:
`coal`, `natural_gas`, `oil`, `nuclear`, `hydro`, `geothermal`, `biomass`,
`battery_storage`, `pumped_storage`, `other`, `solar`, `wind`.

## Layout

- Rows: `timestamp`, UTC hour-beginning, `2018-01-01 00:00:00+00:00` to
  `2022-12-31 23:00:00+00:00` (43,824 rows).
- Columns: one per county, named `"{county} {ST}"` (e.g., `Kern CA`),
  sorted by state then county. Form 860m spells some counties in more than
  one way (e.g., `Kern` and `KERN`); each county has one column, using its
  most common mixed-case spelling (`generation.fleet.counties`). Every file
  has the same columns: the WECC counties with a generator in any category
  in any year. A county with no generator in a category is 0.
- Values are rounded to 0.001 MW. Net generation can be negative (storage,
  station use).

## Method

- **WECC plants.** Form 860m operating generators whose balancing authority
  is a US WECC balancing authority (`build_wecc.BAS`). This includes the
  WECC parts of MT, WY, CO, NM, TX (El Paso), SD and NE and excludes the
  parts of those states in the Eastern or ERCOT interconnections.
  Generators with no balancing authority are included only in states that
  are entirely in WECC (AZ, CA, ID, NV, OR, UT, WA).
- **Capacity.** Sum of generator nameplate MW in each Form 860m month, held
  constant over the hours of the month.
- **Actual.** Each plant's Form 923 monthly net generation by category,
  shaped into hours by its balancing authority's Form 930 hourly net
  generation for that category (`generation.fuels.SHAPES`), then summed by
  county. The monthly totals match Form 923. Form 930 is read one month at a
  time, so a balancing authority month that cannot be read (e.g., a failed
  download) is flat only for that month; the build logs a warning for each
  one. Outlier hours in the Form 930 data are interpolated, negative Form
  930 hours are set to zero except for storage (so a non-storage county is
  negative only in a month in which Form 923 reports negative net
  generation for one of its plants), a storage month whose positive and
  negative Form 930 values nearly cancel is flat, and each
  plant hour is limited to the plant's nameplate capacity with the excess
  moved to other hours of the month, so no county exceeds its capacity
  unless Form 923 reports more energy than the capacity can produce (then
  the month is flat).
- **Missing Form 860m fields.** A generator field a monthly workbook lacks
  (e.g., early 2018) is taken from the same generator in other months of
  the year; the build logs a warning for each such month.

## Caveats

- January–June 2018 is a flat shape within each month (Form 930 fuel data
  starts July 2018); geothermal and biomass are always flat. CEMS, NRC and
  the 2018 backfill in `DESIGN.md` are not implemented yet.
- Form 923 state-fuel increment estimates (plant `99999`) cannot be placed
  in a county and are not included.
- Capacity is nameplate, not summer or winter net capability.
- Values can step at the start of a month, because each month's energy is
  Form 923's for that month and the shape is normalized within the month.

## WECC 240 nodes

`build_nodes.py` aggregates the county files to the generation nodes of
the WECC 240 bus model (`eudoxys/wecc240`). Each county goes to the
nearest generation node given by the `gen` column of `wecc240`
`county_node_map.csv`; a node's value is the sum of its counties, so the
hourly total over the mapped counties is kept. The node files have the
same `timestamp` rows as the county files and one column per node
geohash, sorted.

- Counties are matched by `"{county} {ST}"`. Form 860m spellings that
  differ from the map are corrected (`build_nodes.ALIASES`: `Dona Ana NM`,
  `Sacremento CA`, and `Oceanside CA`, a city, to `San Diego CA`).
- Counties not in the map are dropped with a warning that gives the peak
  MW and energy dropped. With the 2018–2022 files these are mostly wind
  counties outside the WECC 240 footprint (`Curry`, `Lea` and `Quay NM`;
  `Brookings`, `Hyde` and `Pennington SD`; `Kimball NE`; `Morton ND`),
  about 1 GW of wind capacity and 12 TWh, plus Form 860m entries with a
  wrong state (`Nye AZ`, `Morton NY`), `Denton TX` and `Richland MT`.

Review the node files with

```bash
marimo edit data/wecc/review_node_data.py
```

from the repository root. Nodes can be selected by state (from the node
bus county FIPS code) or by WECC 240 area (`BA` column of `wecc240`
`bus_gis.csv`: `CA`, `NW`, `SW`, `BA` (Basin), `RM` (Rocky Mountain)),
which is not an EIA balancing authority.

## Rebuild

```bash
python data/wecc/build_wecc.py --verbose
python data/wecc/build_nodes.py --verbose
```

`build_nodes.py` reads `county_node_map.csv` from GitHub unless
`--mapping` names a local copy.

Form 930 for 2019 and later needs an EIA API key (see `eudoxys/eia`).
