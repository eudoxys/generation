# MANIFEST

Map of the `eudoxys/generation` repository. Every tracked file is covered by
one row or glob below; check with `python .github/check_manifest.py`.
Update this file in the same PR that adds, moves, or deletes a file.

## Start here

1. `CLAUDE.md` — conventions and working rules
2. `DESIGN.md` — agreed design, decisions, planned modules
3. `generation/__init__.py` — package docs and public API
4. `generation/category.py` — `Category`/`Combination` base classes and the shaping method
5. `generation/fuels.py` — EIA codes to categories

## Task index

- Add a generation category: copy `generation/coal.py`; add it to `generation/fuels.py`, the combination in `dispatchable.py` or `nondispatchable.py`, `DATASETS` in `generation/cli.py`, and `generation/__init__.py`; test in `generation/_test/test_categories.py`
- Add a data source (CEMS, NRC, backfill): see `DESIGN.md` "Module layout" (planned modules) and `generation/category.py` (shaping); test with a fake in `generation/_test/conftest.py`
- Change an output column: module docstring example, `generation/__init__.py` Data section, `README.md`, `DESIGN.md` columns table
- Add a CLI option: `generation/cli.py`, `generation/__init__.py` Syntax section, `README.md`
- Fix a test: fakes for Forms 860m/923/930 are in `generation/_test/conftest.py`; `generation/_test/test_eia.py` checks them against the real `eia` classes (sample EIA files in `generation/_test/eia_samples.py`)
- Update for an `eia` API or schema change: fix the call sites in `generation/fleet.py` and `generation/category.py`, then the fakes in `generation/_test/conftest.py` until `generation/_test/test_eia.py` passes
- Update docs: docstrings, then `make docs`
- Add repository data: put it under `data/` with a README; read it with `generation.data.Data` (not installed with the package)
- Release: `pyproject.toml` version; see the eudoxys-package skill checklist

## Package

| Path | Purpose | Notes |
|---|---|---|
| `generation/__init__.py` | package docs, re-exports, `__version__` | pdoc landing page |
| `generation/cli.py` | CLI `main()`, `DATASETS` | entry point `generation`; tested by `_test/test_fleet.py`, `_test/test_categories.py` |
| `generation/fleet.py` | `Fleet`: Form 860m operating generator inventory | tested by `_test/test_fleet.py` |
| `generation/data.py` | `Data`: repository `data/` file, downloaded and cached on first use | tested by `_test/test_data.py` |
| `generation/fuels.py` | energy source/prime mover → 12 categories, dispatchable split, Form 930 codes | tested by `_test/test_categories.py` |
| `generation/category.py` | `Category` and `Combination` base classes; Form 923/930 shaping; caching | tested by `_test/test_categories.py` |
| `generation/coal.py` | `Coal` category | one of 12 near-identical category modules |
| `generation/natural_gas.py` | `NaturalGas` category | |
| `generation/oil.py` | `Oil` category | |
| `generation/nuclear.py` | `Nuclear` category | |
| `generation/hydro.py` | `Hydro` category | |
| `generation/geothermal.py` | `Geothermal` category | |
| `generation/biomass.py` | `Biomass` category | |
| `generation/battery_storage.py` | `BatteryStorage` category | signed |
| `generation/pumped_storage.py` | `PumpedStorage` category | signed |
| `generation/other.py` | `Other` category | |
| `generation/solar.py` | `Solar` category | |
| `generation/wind.py` | `Wind` category | |
| `generation/dispatchable.py` | `Dispatchable` combination | tested by `_test/test_categories.py` |
| `generation/nondispatchable.py` | `Nondispatchable` combination | tested by `_test/test_categories.py` |
| `generation/total.py` | `Total` combination | tested by `_test/test_categories.py` |
| `generation/.gitignore` | generated-output ignores | |

## Tests and review

| Path | Purpose | Notes |
|---|---|---|
| `generation/_test/README.md` | how to run tests | |
| `generation/_test/conftest.py` | fake EIA forms, temporary cache, `GENERATION_CACHEDIR` | |
| `generation/_test/test_fleet.py` | `Fleet` and `fleet` CLI tests | fast, offline |
| `generation/_test/test_categories.py` | category, combination and hourly CLI tests | fast, offline |
| `generation/_test/test_wecc.py` | `data/wecc/build_wecc.py` tests | fast, offline |
| `generation/_test/test_data.py` | `Data` tests | fast, offline (serves files from the checkout's `data/`) |
| `generation/_test/test_eia.py` | real `eia` classes vs. the fakes; `Fleet` and hourly frames built from each | offline (mocked `requests.get`); skipped without `eia` |
| `generation/_test/eia_samples.py` | synthetic Form 860m/923/930 source files for `test_eia.py` | |
| `generation/_review/README.md` | how to run the review notebooks | |
| `generation/_review/review_generation_marimo.py` | marimo plots of `Total` for a county | downloads EIA data |

## Repository

| Path | Purpose | Notes |
|---|---|---|
| `README.md` | user overview | |
| `CLAUDE.md` | assistant guidance | |
| `DESIGN.md` | package design | |
| `MANIFEST.md` | this file | |
| `CONTRIBUTING.md` | contributor guide | approved-issue rule |
| `TODO.md` | roadmap | |
| `COPYRIGHT.md` | copyright holders | |
| `pyproject.toml` | packaging | version here |
| `requirements.txt` | dependencies | |
| `Makefile` | `make docs`, `make test` | |
| `LICENSE` | MIT | |
| `.gitignore` | | GitHub Python template |
| `.gitattributes` | | |
| `.github/workflows/validate.yaml` | CI: pylint and pytest | |
| `.github/workflows/deploy-pages.yaml` | CI: pdoc docs to GitHub Pages | needs Pages source "GitHub Actions" |
| `.github/workflows/approved-issue.yaml` | closes new contributors' PRs without an approved issue | |
| `.github/workflows/assign-issues.yaml` | assigns unassigned issues | |
| `.github/check_manifest.py` | checks this file | |

## Data

Not installed with the package; read with `generation.data.Data`.

| Path | Purpose | Notes |
|---|---|---|
| `data/hydro/README.md` | BPA and WAPA hydro data: sources, columns, time convention | read this, not the data files |
| `data/hydro/**` | BPA (hourly) and WAPA (monthly, CRSP hourly) federal hydro generation, 2018–2022 | ~50 MB; don't read |
| `data/wecc/README.md` | WECC county hourly capacity and net generation by category, 2018–2022 | read this, not the data files |
| `data/wecc/build_wecc.py` | builds the `data/wecc` files from EIA Forms 860m/923/930 | tested by `_test/test_wecc.py`; downloads EIA data |

## Generated

`docs/` holds the pdoc HTML generated by `make docs`. It is not tracked in git.

## Don't read

`docs/` (generated), `.venv/`, caches, `**/__marimo__/` session files, data files over ~1 MB.
