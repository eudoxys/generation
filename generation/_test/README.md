Testing
-------

From the repository root:

	python3.12 -m venv .venv
	. .venv/bin/activate
	python3 -m pip install --upgrade pip
	pip install -e . pytest
	pytest

No credentials are needed and nothing is downloaded: `conftest.py` replaces
`eia.Form860m`, `eia.Form923` and `eia.Form930Fuel` with small fake tables
and points the cache at a temporary folder for each test. `test_eia.py`
checks the fakes against the real `eia` classes. The suite runs in
about 15 seconds.

Environment variables:

  - `GENERATION_CACHEDIR`: cache folder (default: the `cache` package
    default); used by future `network` tests, overridden per test by the
    offline fixture

There are no `network` tests yet.

test_eia.py
-----------

Runs the real `eia.Form860m`, `eia.Form923` and `eia.Form930Fuel` on small
synthetic EIA source files (`eia_samples.py`) served through a mocked
`requests.get`, so nothing is downloaded. Checks that the fakes in
`conftest.py` return the same index, columns and values as the real
classes, and that `Fleet`, `Hydro`, `Solar`, `NaturalGas` and `Total` are
the same when built from either. A change to the `eia` API or output
schema fails here even when the fake-based tests still pass; update the
call sites, then the fakes. Skipped when `eia` isn't installed.

	pytest generation/_test/test_eia.py

test_fleet.py
-------------

Checks `generation.fleet.Fleet` (columns, index, month and state/county
filters, geohash, argument errors) and the `fleet` dataset of the CLI
(output files and formats). Fast and synthetic.

	pytest generation/_test/test_fleet.py

test_categories.py
------------------

Checks `generation.fuels` category mapping, `Category` frames (shape, UTC
index, Form 923 monthly reconciliation, Form 930 shaping and flat
fallback, state-fuel increments excluded, caching and refresh, argument
errors), the `Dispatchable`, `Nondispatchable` and `Total` combinations
(columns and totals), and the hourly CLI datasets. Fast and synthetic.

	pytest generation/_test/test_categories.py
