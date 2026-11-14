import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _(Path):
    datadir = Path("data/wecc")
    return (datadir,)


@app.cell
def _(mo):
    _options = {x.title(): x for x in ["actual", "capacity"]}
    dataset_ui = mo.ui.dropdown(
        options=_options,
        value=list(_options)[0],
        label="Dataset:"
    )
    return (dataset_ui,)


@app.cell
def _(datadir, dataset_ui, mo, os):
    _options = {" ".join(x.split("_")[1:]).split(".")[0].title():x for x in sorted(os.listdir(datadir)) if x.startswith(dataset_ui.value)}
    fuel_ui = mo.ui.dropdown(options=_options,value=list(_options)[0],label="Fuel:")
    return (fuel_ui,)


@app.cell
def _(datadir, fuel_ui, pd):
    data = pd.read_csv(datadir/fuel_ui.value,index_col=[0],parse_dates=[0]).sort_index()
    return (data,)


@app.cell
def _(data, mo):
    _options = sorted({x.split()[-1] for x in data.columns})
    state_ui = mo.ui.dropdown(options=_options,value=None,label="State:")
    return (state_ui,)


@app.cell
def _(data, mo, state_ui):
    _options = [] if state_ui.value is None else sorted([" ".join(x.split()[:-1]) for x in data.columns if x.endswith(state_ui.value)])
    county_ui = mo.ui.dropdown(options=_options,value=None,label="County:",disabled=state_ui is None)
    return (county_ui,)


@app.cell
def _(data, mo):
    _options = sorted(data.index.year.unique())
    year_ui = mo.ui.dropdown(options=_options,value=None,label="Year:")
    return (year_ui,)


@app.cell
def _(calendar, data, mo, year_ui):
    _options = {calendar.month_name[x.month]:x.month for x in data.index if x.year == year_ui.value}
    month_ui = mo.ui.dropdown(options=_options,value=None,label="Month:",disabled=year_ui.value is None)
    return (month_ui,)


@app.cell
def _(county_ui, dataset_ui, fuel_ui, mo, month_ui, state_ui, year_ui):
    mo.hstack([dataset_ui,fuel_ui,state_ui,county_ui,year_ui,month_ui],justify="start")
    return


@app.cell
def _(county_ui, data, mo, month_ui, state_ui, year_ui):
    if year_ui.value is None:
        _dtrange = data.index
    elif month_ui.value is None:
        _dtrange = [x for x in data.index if x.year == year_ui.value]
    else:
        _dtrange = [x for x in data.index if x.year == year_ui.value and x.month == month_ui.value]
    if state_ui.value is None:
        _data = data.loc[_dtrange].sum(axis=1)
    elif county_ui.value is None:
        _data = data.loc[_dtrange][[x for x in data.columns if x.endswith(state_ui.value)]].sum(axis=1)
    else:
        _data = data.loc[_dtrange][f"{county_ui.value} {state_ui.value}"]
    mo.ui.tabs({
        "Plot": _data.plot(),
        "Data": _data,
    })
    return


@app.cell
def _():
    import os
    import calendar
    from pathlib import Path
    import marimo as mo
    import pandas as pd

    return Path, calendar, mo, os, pd


if __name__ == "__main__":
    app.run()
