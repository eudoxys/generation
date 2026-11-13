"""Small synthetic EIA source files for the `eia` integration tests

Each function returns a minimal copy of an EIA source file (Form 860m
workbook, Form 923 zip file, Form 930 reference workbook and API records)
with the same layout as the real one, holding the plants of the offline
fakes in `conftest.py`. The tests in `test_eia.py` serve these files to the
real `eia` classes through a mocked `requests.get`, so a change to the `eia`
parsing or output schema breaks the tests instead of passing silently.

Modelled on `tests/samples.py` of `eudoxys/eia`, which isn't installed with
the `eia` package.
"""

import calendar
import io
import zipfile

import numpy as np
import pandas as pd

from conftest import ROWS, PLANTS

FORM860M_COLUMNS = {
    # EIA workbook header: `ROWS` key
    "Entity ID": "owner",
    "Entity Name": "owner_name",
    "Plant ID": "plant",
    "Plant Name": "plant_name",
    "Plant State": "state",
    "County": "county",
    "Balancing Authority Code": "ba",
    "Sector": "sector",
    "Generator ID": "generator",
    "Unit Code": "unit",
    "Nameplate Capacity (MW)": "nameplate_mw",
    "Net Summer Capacity (MW)": "summer_mw",
    "Net Winter Capacity (MW)": "winter_mw",
    "Energy Source Code": "fuel",
    "Prime Mover Code": "pm",
    "Latitude": "latitude",
    "Longitude": "longitude",
}
"""Form 860m workbook headers of the `ROWS` columns"""


def form860m_workbook(year, month, subset="Operating"):
    """Form 860m generator workbook holding `ROWS`

    Workbooks before November 2020 have one title row above the header;
    later workbooks have two. A footnote row follows the data.
    """
    skip = 2 if year > 2020 or (year == 2020 and month > 10) else 1
    columns = list(FORM860M_COLUMNS)
    rows = [[ROWS[FORM860M_COLUMNS[x]][n] for x in columns] for n in range(len(ROWS["plant"]))]
    blank = [""] * (len(columns) - 1)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        pd.DataFrame([["title"] + blank] * skip + [columns] + rows + [["footnote"] + blank]) \
            .to_excel(writer, sheet_name=subset, index=False, header=False)
    return buffer.getvalue()


def form923_zip(year):
    """Form 923 zip file whose generation and fuel workbook holds `PLANTS`

    Monthly net generation is each plant's average MW times the hours in
    the month, as in `conftest.FakeForm923`.
    """
    months = [calendar.month_name[x] for x in range(1, 13)]
    columns = ["Plant Id", "Plant Name", "Plant State", "Balancing\nAuthority Code",
        "Reported\nPrime Mover", "Reported\nFuel Type Code"] \
        + [f"Quantity\n{x}" for x in months] + [f"Netgen\n{x}" for x in months]
    hours = [calendar.monthrange(year, x)[1] * 24 for x in range(1, 13)]
    rows = [[plant, f"Plant {plant}", state, ba, pm, fuel] + ["1"] * 12
            + [str(mw * x) for x in hours]
        for state, ba, plant, pm, fuel, mw in PLANTS]
    sheet = io.BytesIO()
    pd.DataFrame([["title"] + [""] * (len(columns) - 1)] * 5 + [columns] + rows) \
        .to_excel(sheet, index=False, header=False, engine="openpyxl")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as fh:
        fh.writestr(f"EIA923_Schedules_2_3_4_5_M_12_{year}_Final.xlsx", sheet.getvalue())
        fh.writestr("readme.txt", "other file")
    return buffer.getvalue()


def form930_reference(*codes):
    """Form 930 reference workbook listing the balancing authority `codes`"""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        pd.DataFrame({"BA Code": list(codes)}).to_excel(writer, sheet_name="BAs", index=False)
        pd.DataFrame({"Region/Country Code": ["CAL", "NW"]}) \
            .to_excel(writer, sheet_name="Regions", index=False)
    return buffer.getvalue()


def form930_fuel_records(year, month, respondent):
    """Form 930 `fuel-type-data` API records for one month

    Periods are UTC hour-ending. BANC reports a diurnal `SUN` peaking in the
    hour beginning 20:00Z and a constant `WAT`, as in
    `conftest.FakeForm930Fuel`; other respondents report nothing.
    """
    if respondent != "BANC":
        return []
    start = pd.Timestamp(year=year, month=month, day=1)
    hours = pd.date_range(start, start + pd.DateOffset(months=1), freq="h", inclusive="left")
    records = []
    for hour in hours:
        period = (hour + pd.Timedelta(hours=1)).strftime("%Y-%m-%dT%H")
        sun = 100 * max(0.0, np.cos(2 * np.pi * (hour.hour - 20) / 24))
        for code, value in [("SUN", sun), ("WAT", 50.0)]:
            records.append({"period": period, "respondent": respondent,
                "fueltype": code, "value": value})
    return records
