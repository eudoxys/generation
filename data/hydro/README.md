# Hydro generation data for the WECC model (2018–2022)

Historical generation of the federal hydropower plants marketed by the
Bonneville Power Administration (BPA) and the Western Area Power
Administration (WAPA), compiled from public agency sources for the
WECC 240-bus model.

Every value comes from a public agency source (USACE, USBR, WAPA, EIA).
Values are stored as published. No unit conversion, gap filling or outlier
removal has been applied. The one exception is the added column
`power_MW_adjust` in the BPA files, described below.

Compiled by Yi Lu (Stanford University).

## Contents

```
data/hydro/
  README.md                       this file
  WECC_Hydro_Data_Overview.docx   overview of both datasets
  VERIFICATION_REPORT.docx        checks against independent sources
  BPA_dams/                       14 BPA dams, hourly
  WAPA_dams/                      5 WAPA projects, monthly (CRSP also hourly)
```

| Dataset | Plants | Resolution | Period | Source |
|---|---|---|---|---|
| `BPA_dams/USACE_CWMS_hourly/` | 14 BPA dams | hourly | 2018-01 to 2022-12 | USACE Northwestern Division CWMS |
| `WAPA_dams/*/USBR_RISE_monthly/` | 39 USBR plants | monthly | 2018-01 to 2022-12 | USBR RISE |
| `WAPA_dams/3_CRSP/WAPA_SCADA_hourly/` | 6 CRSP plants | hourly | 2018-01 to 2022-04 | WAPA CRSP SCADA reports |
| `WAPA_dams/4_Pick_Sloan/EIA923_monthly_USACE_mainstem/` | 6 USACE Missouri River mainstem dams | monthly | 2018-01 to 2022-12 | EIA-923 |

## Time convention

All hourly timestamps are **UTC, hour-ending**: the row `2018-01-01 01:00:00`
holds the hour from 00:00 to 01:00 UTC. The `generation` package design uses
hour-beginning timestamps, so subtract one hour to convert.

Monthly files are calendar months in plant local time. The RISE files also
give the UTC start of each month (`period_start_utc`).

## BPA dams (hourly)

There is one CSV per dam, with 43,824 hourly rows each. The 14 dams are
Albeni Falls, Bonneville, Chief Joseph, Dworshak, Grand Coulee, Hungry Horse,
Ice Harbor, John Day, Libby, Little Goose, Lower Granite, Lower Monumental,
McNary and The Dalles. Ten of them are the "Big 10" run-of-river dams.

| File | Content |
|---|---|
| `dam_list.csv` | Dam code, name, owner, river, state, Big 10 flag, data file, EIA plant id, EIA-860 nameplate MW |
| `USACE_CWMS_hourly/<CODE>_<Name>_hourly_2018_2022_UTC.csv` | Hourly data, one file per dam |
| `USACE_CWMS_hourly/data_dictionary.csv` | Column definitions, units and CWMS parameter names |
| `USACE_CWMS_hourly/series_used.csv` | Exact CWMS time-series id behind every column |
| `power_MW_adjustments.csv` | Change log of the 7 hours where `power_MW_adjust` differs from `power_MW` |
| `manual_download_links.txt` | Direct USACE download link for each dam, to reproduce the files |
| `BPA_dams_README.docx` | Full documentation |

Main columns:

| Column | Unit | Description |
|---|---|---|
| `datetime_utc` | | UTC, hour-ending |
| `power_MW` | MW | Plant total generation, exactly as published by CWMS |
| `power_MW_adjust` | MW | Same as `power_MW`, with 7 obvious recording errors corrected. **Use this column for analysis.** |
| `station_service_MW`, `spinning_reserve_MW`, `capacity_available_MW` | MW | Where available |
| `outflow_kcfs`, `genflow_kcfs`, `spill_kcfs`, `inflow_kcfs` | kcfs | Total, turbine, spill and inflow |
| `forebay_elev_ft`, `tailwater_elev_ft` | ft | Water levels |
| `storage_kaf` | kaf | Reservoir storage |

Not every dam has every column. `data_dictionary.csv` lists which dams have
which.

### Corrected recording errors

A value is corrected only if all three of these hold:

1. It is isolated: the neighbouring hours agree with each other and the
   turbine flow is steady.
2. It is at least 5 times higher or lower than the output implied by the
   measured turbine flow (flow × the dam's 7-day median MW per kcfs).
3. One single recording error (one extra digit, or a decimal point shifted
   by 10 or 100) brings it within 5 % of the flow-implied output.

Seven hours meet this rule:

| Dam | Hour (UTC) | `power_MW` | `power_MW_adjust` | Recording error |
|---|---|---|---|---|
| Chief Joseph | 2018-01-30 07:00 | 12,131 | 1,213 | extra digit |
| Chief Joseph | 2018-02-17 16:00 | 10,992 | 1,992 | extra digit |
| Chief Joseph | 2018-03-18 15:00 | 10,936 | 1,093 | extra digit |
| Grand Coulee | 2018-06-25 12:00 | 27,620 | 2,762 | extra digit |
| Grand Coulee | 2018-09-25 01:00 | 22,284 | 2,284 | extra digit |
| Grand Coulee | 2018-10-28 20:00 | 18.1 | 1,810 | decimal point (×100) |
| Grand Coulee | 2022-11-28 11:00 | 16.9 | 1,690 | decimal point (×100) |

In every other hour `power_MW_adjust` equals `power_MW`.

### Known issues

- **Grand Coulee:** the annual sum of `power_MW` is 8–12 % above the
  generation reported by USBR and EIA-923, although turbine flow matches
  USBR exactly. The cause is not confirmed; one possibility is apparent
  rather than real power. For absolute energy, scale the hourly shape to
  USBR's monthly totals (RISE series 5257:
  https://data.usbr.gov/catalog/4194/item/5257).
- **McNary:** about 7 % above EIA-923 in 2021–2022, and within 1 % in
  2018–2020.
- Hungry Horse (2018, 2019, 2021) and Dworshak (2018) differ from EIA-923
  by 3–7 %. The other dams match within about 3 %. See
  `VERIFICATION_REPORT.docx`.

## WAPA projects

WAPA does not publish hourly generation for most of its plants. Only the
six CRSP plants have public hourly data, from WAPA's SCADA reports. All
other plants are monthly. All WAPA values are kept exactly as published.

| Folder | WAPA project | Plants |
|---|---|---|
| `1_Boulder_Canyon/` | Boulder Canyon | Hoover |
| `2_Parker_Davis/` | Parker-Davis | Davis, Parker |
| `3_CRSP/` | Colorado River Storage Project | Blue Mesa, Crystal, Flaming Gorge, Fontenelle, Glen Canyon, Morrow Point (monthly and hourly) |
| `4_Pick_Sloan/` | Pick-Sloan Missouri Basin Program | 20 USBR plants (RISE) and 6 USACE mainstem dams (EIA-923) |
| `5_Central_Valley/` | Central Valley Project | Folsom, Judge Francis Carr, Keswick, Lewiston, New Melones, Nimbus, Shasta, Spring Creek, Stampede, Trinity |

| File | Content |
|---|---|
| `plant_list.csv` | Every plant: project, owner, state, data source and data file |
| `data_dictionary.csv` | Column definitions and units of every file type |
| `sources.csv` | Source page and direct download link behind every series |
| `WAPA_dams_README.docx` | Full documentation |

Units:
- RISE monthly files are in kWh (net, gross, station service and pumping energy) and kW (installed capacity).
- EIA-923 files are in MWh (net generation).
- SCADA hourly files are in MW.

Notes:
- The CRSP SCADA reports are in Mountain Standard Time. They were converted
  to UTC by adding 7 hours. The original date and hour are kept in
  `scada_local_date` and `scada_hour_ending`.
- RISE monthly values for five CRSP plants (all but Glen Canyon) differ from
  EIA-923 in 2018–2020 and match from 2021. See `VERIFICATION_REPORT.docx`.
- Of the six USACE mainstem dams, only Fort Peck is connected to WECC.
  Public sources give no fixed split of its units between the Western and
  Eastern Interconnections.

## Sources

- USACE Northwestern Division CWMS: https://www.nwd-wc.usace.army.mil/dd/common/dataquery/www/ (direct links per dam in `BPA_dams/manual_download_links.txt`)
- USBR Reclamation Information Sharing Environment (RISE): https://data.usbr.gov/
- WAPA CRSP historical power plant data: https://www.wapa.gov/about-wapa/regions/crsp/about-crsp/operations-maintenance/historical-power-plant-data/
- EIA-923: https://www.eia.gov/electricity/data/eia923/
- EIA-860: https://www.eia.gov/electricity/data/eia860/
