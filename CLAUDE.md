# CLAUDE.md

Guidance for Claude when working in the `eudoxys/generation` repository.
General Eudoxys package conventions are in the `eudoxys-package` skill
(`eudoxys/claude`); this file records only what is specific to this package.

## What this is

Hourly, county-level models of US utility-scale net generation by energy
source category, built from EIA Form 860m (plants), Form 923 (monthly plant
net generation) and Form 930 (hourly balancing-authority generation by fuel).
Python 3.12, alpha (`version = "0.0.0"`, unreleased). Output frames follow
the `eudoxys/loads` paradigm.

- Docs site: https://www.eudoxys.com/generation (pdoc from docstrings)
- Maintainer: David P. Chassin
- CLI entry point: `generation` -> `generation.cli:main`

## Where things are

- `MANIFEST.md`: map of every file, a task index, and what not to read.
  Read it first instead of listing folders.
- `DESIGN.md`: agreed design, numbered decisions, and planned modules. Follow
  its decisions; ask before departing from one.

Sibling Eudoxys dependencies:

- `eia`: `Form860m`, `Form923(by="plant")`, `Form930Fuel`
- `cache`: on-disk cache for category frames
- `geohash`: plant location geohash

## Core conventions

- Every hourly generation frame is `Class(state,county,year,*,refresh=False)`
  (decision #16) and subclasses `Category` (built from plants) or
  `Combination` (built from other frames) in `generation/category.py`.
- One module per category; `dispatchable.py`, `nondispatchable.py` and
  `total.py` combine them (decision #15). Combinations keep each
  contributor's total column and add their own (decision #17).
- Category membership, dispatchable split and Form 930 shaping codes live in
  `generation/fuels.py`.
- Index `timestamp`, tz-aware UTC, hour-beginning (decision #2). Power
  columns end in `_MW` (decision #13); an hourly mean MW equals MWh.
- Net generation can be negative (storage, station use).
- Missing Form 930 data falls back to a flat monthly shape. When
  `Form930Fuel` has no data for a BA-year (no API key, unknown BA, year
  before 2019) a `UserWarning` is issued; a BA that doesn't report a
  category's code, or a non-positive monthly total, is flat silently. Other
  errors (e.g., `TypeError` from an `eia` API change) propagate.
- Category frames are cached as
  `generation/0/{ST}/{county}/{year}/{category}.csv.gz`; bump
  `Category.VERSION` when the cached format changes.

## Style

No spaces after commas in calls and signatures in package code; pdoc
docstrings with dashed section underlines; `_logger =
logging.getLogger(__file__)` in each module. Tests use ordinary PEP 8
spacing.

## Build, test, docs

```bash
python3.12 -m venv .venv && . .venv/bin/activate
pip install --upgrade pip && pip install -e . pytest
pytest
make docs
```

The test suite is offline (fakes for Forms 860m, 923 and 930 in
`generation/_test/conftest.py`) and takes seconds. Real runs download EIA
data and need an EIA API key for Form 930. CI (`validate.yaml`) runs pylint
(informational) and pytest on Python 3.12.

## Known rough edges (don't "fix" silently; mention or ask)

- `docs/` is committed and the repo still has GitHub's branch-based
  `pages-build-deployment`. `deploy-pages.yaml` needs the Pages source set to
  "GitHub Actions"; after that, `docs/` can be removed from git.
- CEMS, NRC and the 2018 backfill are planned (`DESIGN.md`) but not
  implemented; those hours use a flat shape. `eia.Form930Fuel` starts in
  2019, so all of 2018 is flat (with a warning), not just Jan–Jun.
- AGC flags, county geohash keys, and the long `county_generation` table are
  not implemented yet.
- `Fleet` has a different constructor (`Fleet(state,county,year,*,months)`,
  multi-month, one row per unit-month) from the hourly frames.
- `marimo` and `matplotlib` are runtime requirements only because of the
  `_review` notebook.
- The CLI docstring example output is from the old `Generation` class and
  was not regenerated against live data.

## Working rules

- Don't commit caches, EIA downloads, or generated output.
- When a public signature, column or output changes, update the module
  docstring example, `generation/__init__.py`, `README.md`, and `DESIGN.md`
  in the same PR.
- Update `MANIFEST.md` when adding, moving, or deleting files, and run
  `python .github/check_manifest.py`.
- Conventional small case: `Total("CA","Kern",2020)`. Avoid state- or
  nation-wide builds unprompted; they download a lot of Form 930 data.
