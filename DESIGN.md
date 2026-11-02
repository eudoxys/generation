# eudoxys/generation — package design (draft 5)

Status: design agreed, 2026-10-21; module structure revised 2026-10-21

## Purpose

Hourly, county-level models of US utility-scale generation, assembled from
EIA, EPA and other public data, following the `eudoxys/loads` design
paradigm. Rooftop/distributed PV is excluded (it is netted into
`loads` as `elec_dg_MW`). Coverage is 2018-01-01 00:00Z to the latest
available month.

## Decisions settled

| # | Decision |
|---|---|
| 1 | Net generation |
| 2 | UTC, hour-beginning timestamps |
| 3 | 12 energy-source categories |
| 4 | Utility-scale only (EIA-860M plants); no rooftop DG |
| 4b | Start Jan 2018; Jan–Jun 2018 needs a backfill (EIA-930 fuel mix starts Jul 2018) |
| 5 | Long tables are sparse; unstacked (wide) totals fill missing with 0 |
| 6 | Output format: `.csv` if <100 MB, else `.csv.gz` if <100 MB, else `.parquet` |
| 7 | Counties are keyed by centroid `geohash` from `eudoxys/fips`, not FIPS |
| 8 | The unit inventory module is `fleet.py` (class `Fleet`, formerly `Generation` in `generation.py`) |
| 9 | The CEMS loader lives in this package (`cems.py`) |
| 10 | Plants carry two flags: `dispatchable` and `agc`. Nuclear is dispatchable without AGC |
| 11 | Nuclear backfill uses NRC daily reactor power status |
| 12 | No backfill acceptance test yet; review the backfilled values first |
| 13 | Power columns keep the `_MW` suffix |
| 14 | Default `agc` assignments accepted for now |
| 15 | One module per category; `dispatchable.py` and `nondispatchable.py` combine categories; `total.py` combines both |
| 16 | Every generation data frame is constructed as `Class(state,county,year)` and returns hourly MW for the county |
| 17 | A data frame built from other data frames keeps a column for each contributor and adds a total `_MW` column |

## Conventions inherited from `eudoxys/loads`

- Data classes subclass `pd.DataFrame` and do all work in `__init__`.
- Cache-first loading via `eudoxys/cache`, with `CACHEDIR` and `refresh`.
- `makeargs` classmethod for CLI dispatch.
- Hourly index named `timestamp`, tz-aware UTC.
- Power columns use the `_MW` suffix. An hourly mean MW equals MWh for that
  hour, so `_MW` is used instead of `_MWh` for consistency with `loads`.
- Column names are lowercase, matching the `Fleet` class.
- House style: no spaces after commas in calls, pdoc docstrings, `_logger`.

## Module layout

```
generation/
  fleet.py          Fleet: unit inventory from EIA-860M, Fleet(state,county,year)
  fuels.py          EIA energy-source/prime-mover codes -> 12 categories,
                    dispatchable split, and 930 shaping code per category
  category.py       Category (plant-built) and Combination (frame-built) base
                    classes, and the shaping method
  # dispatchable categories
  coal.py           Coal
  natural_gas.py    NaturalGas
  oil.py            Oil
  nuclear.py        Nuclear
  hydro.py          Hydro (conventional)
  geothermal.py     Geothermal
  biomass.py        Biomass
  battery_storage.py BatteryStorage (signed; may be negative)
  pumped_storage.py PumpedStorage (signed; may be negative)
  other.py          Other
  # non-dispatchable categories
  solar.py          Solar (utility-scale PV and solar thermal)
  wind.py           Wind (onshore and offshore)
  # combinations
  dispatchable.py   Dispatchable: the 10 dispatchable categories
  nondispatchable.py Nondispatchable: solar and wind
  total.py          Total: Dispatchable + Nondispatchable
  cli.py            `generation YEAR [MONTH] [STATE] [-C COUNTY] [-D DATASET] ...`
  # planned
  plants.py         plant -> county geohash crosswalk and plant flags
  cems.py           EPA CAMPD hourly unit gross load
  nrc.py            NRC daily power reactor status (nuclear backfill)
  backfill.py       Jan–Jun 2018 hourly shapes (see below)
  validate.py       reconciliation against 923 (monthly) and 930 (hourly BA)
  io.py             save()/load() implementing the size-based format rule
```

### Constructor and columns

Every generation data frame has the same constructor,

```python
Class(state:str,county:str,year:int,*,refresh:bool=False)
```

and returns one row per UTC hour-beginning `timestamp` of the year.

| class | columns |
|---|---|
| category, e.g. `Coal` | `plant_{id}_MW` per contributing plant, `coal_MW` |
| `Dispatchable` | `coal_MW` … `other_MW` (10 categories), `dispatchable_MW` |
| `Nondispatchable` | `solar_MW`, `wind_MW`, `nondispatchable_MW` |
| `Total` | all `Dispatchable` and `Nondispatchable` columns, `total_MW` |

A combination keeps the total column of each category it combines and all
columns of each combination it combines, then adds its own total. Category
frames are cached on disk (`eudoxys/cache`, `generation/0/{ST}/{county}/{year}/{category}.csv.gz`).

The county-hour-fuel long table, plant flags and wide multi-county tables
described below are assembled from these per-county frames.

## Plant flags: `dispatchable` and `agc`

The flags are set per generator from fuel category and EIA prime mover in
`fuels.py`, then rolled up to the plant/fuel level. A plant/fuel is `agc`
if any of its generators is.

No public dataset records which units participate in AGC, so the `agc`
defaults below are assumptions. They can be overridden per plant (or per
generator) by a curated `agc.csv` of `id,unit,agc` rows.

| category | prime movers | dispatchable | agc (default) |
|---|---|---|---|
| coal | ST | yes | yes |
| natural_gas | CT, CA, CS, GT | yes | yes |
| natural_gas | ST | yes | yes |
| natural_gas | IC | yes | no |
| oil | GT, ST | yes | yes |
| oil | IC | yes | no |
| nuclear | ST | yes | **no** |
| hydro | HY | yes | yes |
| geothermal | ST, BT | yes | no |
| biomass | ST, GT, IC | yes | no |
| battery_storage | BA | yes | yes |
| pumped_storage | PS | yes | yes |
| other | (any) | yes | no |
| solar | PV, ST | no | no |
| wind | WT, WS | no | no |

## Hourly sources by category

| category | primary hourly source | monthly anchor |
|---|---|---|
| coal | CEMS | 923 |
| natural_gas | CEMS, else 930 NG residual | 923 |
| oil | CEMS, else 930 OIL residual | 923 |
| nuclear | 930 NUC | 923 |
| hydro | 930 WAT | 923 |
| geothermal | flat within month | 923 |
| biomass | CEMS if present, else flat | 923 |
| battery_storage | 930 (when reported), else 0 | 923 |
| pumped_storage | 930 WAT residual / 923 | 923 |
| other | 930 OTH | 923 |
| solar | 930 SUN | 923 |
| wind | 930 WND | 923 |

## Allocation method (Jul 2018 onward)

1. **Plants.** EIA-860M operating generators → plant → county geohash, via
   state and county name matched against `fips.Counties()`.
2. **CEMS units.** Use hourly gross load scaled to net using the plant's
   monthly 923 net/gross ratio.
3. **Non-CEMS plants.** Take 923 monthly net generation and shape it with
   the BA's 930 hourly profile for that fuel, after the CEMS share is
   removed.
4. **Aggregate.** Sum plant-hours to county-hours.
5. **Reconcile.** Plant-hours sum exactly to 923 monthly. Each BA's
   county sums are compared with 930 hourly, and differences are reported
   rather than forced.

## Backfill for Jan–Jun 2018

EIA-930 BA net generation (`NG`) exists for this period; only the fuel split
is missing. CEMS and 923 are both complete for 2018.

1. **CEMS fossil** is measured, so no backfill is needed.
2. **Nuclear** uses 923 monthly, shaped by NRC daily reactor power status
   (% power, held constant within each day). This captures refueling
   outages and derates.
3. **Solar** uses 923 monthly, shaped by a clear-sky/NSRDB irradiance
   profile at the plant (`eudoxys/weather`, already a `loads` dependency).
4. **Wind, hydro and other** share the hourly residual: 930 BA `NG` minus
   steps 1–3. The residual is split in proportion to each fuel's 923 monthly
   share within the BA, clipped at 0 and renormalized to 923. If the
   residual is unusable (e.g. negative for most of a month), the fallback
   shape is the same calendar month of 2019 from 930.
5. **Review, not acceptance.** The same backfill is also run on Jul–Dec
   2018, where 930 fuel data exists. `validate.py` reports hourly RMSE and
   correlation by BA and fuel alongside plots of backfilled vs. reported
   shapes. No pass/fail threshold is set until those values have been
   reviewed.

## Output tables

### `county_generation` (long, sparse; the canonical output)

Key: `(timestamp, geohash, fuel)`. A row is present only if at least one
plant contributes.

| column | dtype | notes |
|---|---|---|
| `timestamp` | `datetime64[ns, UTC]` | hour-beginning; index |
| `geohash` | `str` (6 chars) | county centroid, `fips.Counties().GEOHASH` |
| `fuel` | `category` | 12 categories above |
| `net_MW` | `float64` | hourly mean MW (= MWh); can be negative |
| `agc_MW` | `float64` | portion of `net_MW` from AGC plants |
| `plants` | `int16` | contributing plants |
| `measured` | `float32` | fraction of MWh from CEMS (0–1) |
| `method` | `category` | `930`, `backfill`, `flat` (dominant shaping method) |

`dispatchable` is not stored on this table because it is fixed by `fuel`.
`agc` varies by plant within a fuel (e.g. gas IC engines vs. combined
cycle), so the AGC share of each row is carried in `agc_MW`.

Example rows (values are illustrative only):

```
timestamp                  geohash fuel        net_MW  agc_MW plants measured method
2018-07-01 19:00:00+00:00  9q9q1v  natural_gas   88.2    88.2      1     1.00    930
2018-07-01 19:00:00+00:00  9q9q1v  solar          5.4     0.0      2     0.00    930
2018-07-01 19:00:00+00:00  c25nbr  nuclear     1150.0     0.0      1     0.00    930
2018-07-01 19:00:00+00:00  c25nbr  wind         212.6     0.0      4     0.00    930
2018-07-01 19:00:00+00:00  c27h96  hydro       1630.4  1630.4      2     0.00    930
```

### Dimension tables

- **`counties`** comes straight from `fips.Counties()`: `geohash`, `ST`,
  `COUNTY`, `FIPS`, `LAT`, `LON`, `TZOFFSET`, `DST`, `REGION`. FIPS is kept
  as an attribute, not as the key.
- **`plants`**, keyed by `(id, fuel)` because one plant can hold several
  categories: `name`, `state`, `county`, `geohash` (county),
  `plant_geohash` (plant location, 6 chars), `region` (BA),
  `nameplate_MW`, `dispatchable`, `agc`.

### `plant_generation` (intermediate, kept for audit)

Key: `(timestamp, id, fuel)`. Columns: `net_MW`, `method`.

### Unstacked total (wide; `loads`-compatible)

Index `timestamp`, one column per county `geohash`, values are the total
`net_MW` summed over fuels, with missing values filled as 0. This mirrors
`loads/examples/county_total.csv.gz`. Per-fuel and filtered wide tables are
available via `Total(...).unstack(fuel="wind")` and
`Total(...).unstack(agc=True)`.

## Files and the format rule

`io.save(df,basename)` writes `basename.csv`. If that file is ≥100 MB it
writes `.csv.gz` instead. If the `.csv.gz` is also ≥100 MB, it writes
`.parquet`. `io.load(basename)` reads whichever of the three exists.

Partitioning: `{ST}/{year}/county_generation`, `{ST}/{year}/plant_generation`
and `{year}/county_total`.

Rough sizes (estimates, to confirm on real data):

- Long table: ~70 bytes/row. California is ~60 counties × ~5 fuels × 8,760
  h ≈ 180 MB CSV per year, so it would be stored as `.csv.gz`. Most states
  stay under 100 MB as plain `.csv`.
- Wide national total: 8,760 × 3,142 ≈ 200+ MB CSV, so `.csv.gz`.
- The national long table for one year (~4 GB CSV) would hit `.parquet`,
  which is why the long table is partitioned by state.

## Dependencies and gaps in sibling packages

| need | status |
|---|---|
| 860M generator inventory | `eia.Form860m` ✔ |
| 923 monthly **by plant** | `eia.Form923(by="plant")`, eudoxys/eia PR #1 (open) |
| 930 hourly **by fuel** | `eia.Form930Fuel`, eudoxys/eia PR #1 (open); also fixes `Form930` to UTC hour-beginning and allows 2018 |
| CEMS hourly unit load | none; new `generation/cems.py` (EPA CAMPD API) |
| NRC reactor status | none; new `generation/nrc.py` |
| county geohash | `fips.Counties().GEOHASH` ✔ (6 chars, unique across all 3,142) |
| caching | `eudoxys/cache` ✔ |

## Known issues to handle

- **County name matching.** 860M gives county names, not FIPS, so a
  crosswalk is needed for spelling variants (Saint/St., DeKalb, independent
  cities in VA/MO/MD/NV, and Alaska borough names such as
  "Juneau City and" in `fips`).
- **Connecticut.** `fips` has the 8 legacy counties. Newer EIA files may
  report the 9 planning regions, which need a mapping back to the legacy
  counties.
- **AGC defaults are assumptions.** They are a starting point until a
  curated `agc.csv` is assembled.

## Open questions

None at this time.
