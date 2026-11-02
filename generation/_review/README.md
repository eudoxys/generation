Review
------

Notebooks for looking at generation results. They are not part of the public
API and are not tested.

`review_generation_marimo.py`
-----------------------------

Shows the `generation.total.Total` data of one county and year as hourly,
monthly and daily-profile plots with summary statistics. Run it from the
repository root with

	marimo edit generation/_review/review_generation_marimo.py

The first run for a county downloads EIA data (Form 930 needs an EIA API
key) and caches the category frames.
