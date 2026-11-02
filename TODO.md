# Fleet and categories

- [x] Generator inventory from Form 860m (see `generation.fleet`)

- [x] 12 category modules shaped by Form 923 and Form 930 (see `generation.category`)

- [x] Dispatchable, non-dispatchable and total combinations (see `generation.total`)

# Hourly sources

- [ ] CEMS hourly unit gross load (`cems.py`, decision #9)

- [ ] NRC daily reactor status for the nuclear backfill (`nrc.py`, decision #11)

- [ ] Jan–Jun 2018 backfill (`backfill.py`, decision #4b)

# Outputs

- [ ] Plant flags `dispatchable` and `agc` with `agc.csv` overrides (`plants.py`, decision #10)

- [ ] County geohash keys (decision #7)

- [ ] Long `county_generation` table and the wide unstacked total

- [ ] Size-based output format rule (`io.py`, decision #6)

# Validation

- [ ] Reconciliation against Form 923 and Form 930 (`generation/_validate/`)

- [ ] Review backfill shapes on Jul–Dec 2018 (decision #12)

# Release

- [ ] Switch GitHub Pages to "GitHub Actions" and untrack `docs/`

- [ ] First release `YEAR.MONTH.0`
