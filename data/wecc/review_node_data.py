import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    This notebook reviews the WECC 240 node capacity and actual generation
    files (`node_*.csv.gz`) made by `build_nodes.py`. Nodes can be selected
    by state (from the node bus county FIPS code) or by WECC 240 area (`BA`
    column of `wecc240` `bus_gis.csv`: `CA`, `NW`, `SW`, `BA` (Basin) and
    `RM` (Rocky Mountain)).
    """)
    return


@app.cell
def _(Path):
    datadir = Path("data/wecc")
    BUS_GIS = "https://raw.githubusercontent.com/eudoxys/wecc240/main/wecc240/data/bus_gis.csv"
    STATES = {
        "04": "AZ", "06": "CA", "08": "CO", "16": "ID", "30": "MT", "31": "NE",
        "32": "NV", "35": "NM", "41": "OR", "46": "SD", "48": "TX", "49": "UT",
        "53": "WA", "56": "WY",
    }
    return BUS_GIS, STATES, datadir


@app.cell
def _(BUS_GIS, STATES, pd):
    _gis = pd.read_csv(BUS_GIS, dtype={"FIPS": str})
    nodes = _gis.dropna(subset=["GEOHASH"]).groupby("GEOHASH").agg(
        name=("NAME", "first"),
        ba=("BA", "first"),
        fips=("FIPS", "first"),
    )
    nodes["state"] = [STATES.get(str(x)[:2], str(x)[:2]) if isinstance(x, str) else None for x in nodes["fips"]]
    return (nodes,)


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
    _prefix = f"node_{dataset_ui.value}_"
    _options = {x[len(_prefix):].split(".")[0].replace("_", " ").title(): x for x in sorted(os.listdir(datadir)) if x.startswith(_prefix)}
    fuel_ui = mo.ui.multiselect(options=_options, value=list(_options), label="Fuel:")
    return (fuel_ui,)


@app.cell
def _(mo):
    group_ui = mo.ui.dropdown(options={"State": "state", "BA": "ba"}, value="State", label="By:")
    return (group_ui,)


@app.cell
def _(data, group_ui, mo, nodes):
    _options = sorted({x for x in nodes.loc[nodes.index.intersection(data.columns), group_ui.value].dropna()})
    area_ui = mo.ui.dropdown(options=_options, value=None, label=f"{group_ui.selected_key}:")
    return (area_ui,)


@app.cell
def _(area_ui, data, group_ui, mo, nodes):
    _nodes = [] if area_ui.value is None else [x for x in data.columns if x in nodes.index and nodes.loc[x, group_ui.value] == area_ui.value]
    _options = {f"{nodes.loc[x, 'name']} ({x})": x for x in sorted(_nodes, key=lambda x: nodes.loc[x, "name"])}
    node_ui = mo.ui.dropdown(options=_options, value=None, label="Node:", disabled=area_ui.value is None)
    return (node_ui,)


@app.cell
def _(data, mo, pd):
    _options = sorted(data.index.year.unique()) if data.index.size > 0 else pd.DatetimeIndex([])
    year_ui = mo.ui.dropdown(options=_options, value=None, label="Year:")
    return (year_ui,)


@app.cell
def _(calendar, data, mo, year_ui):
    _options = {calendar.month_name[x.month]: x.month for x in data.index if x.year == year_ui.value}
    month_ui = mo.ui.dropdown(options=_options, value=None, label="Month:", disabled=year_ui.value is None)
    return (month_ui,)


@app.cell
def _(area_ui, dataset_ui, fuel_ui, group_ui, mo, month_ui, node_ui, year_ui):
    mo.hstack([dataset_ui, fuel_ui, group_ui, area_ui, node_ui, year_ui, month_ui], justify="start")
    return


@app.cell
def _(area_ui, data, group_ui, mo, month_ui, node_ui, nodes, year_ui):
    if year_ui.value is None:
        _dtrange = data.index
    elif month_ui.value is None:
        _dtrange = data.index[data.index.year == year_ui.value]
    else:
        _dtrange = data.index[(data.index.year == year_ui.value) & (data.index.month == month_ui.value)]
    if area_ui.value is None:
        _data = data.loc[_dtrange].sum(axis=1)
        _title = "WECC total"
    elif node_ui.value is None:
        _columns = [x for x in data.columns if x in nodes.index and nodes.loc[x, group_ui.value] == area_ui.value]
        _data = data.loc[_dtrange, _columns].sum(axis=1)
        _title = f"{group_ui.selected_key} {area_ui.value} ({len(_columns)} nodes)"
    else:
        _data = data.loc[_dtrange, node_ui.value]
        _title = f"{nodes.loc[node_ui.value, 'name']} ({node_ui.value})"
    mo.ui.tabs({
        "Plot": mo.mpl.interactive(_data.plot(title=_title, xlabel="Date/Time (UTC)", ylabel="Power (MW)", grid=True, figsize=(10, 7))) if _data.index.size > 0 else mo.md("No result"),
        "Data": _data if _data.index.size > 0 else mo.md("No result"),
        "Nodes": mo.ui.table(nodes.loc[nodes.index.intersection(data.columns)].reset_index(), selection=None, page_size=50),
    })
    return


@app.cell
def _(datadir, fuel_ui, mo, pd):
    with mo.status.progress_bar(title="Reading data...", total=len(fuel_ui.value), remove_on_exit=True) as _bar:
        data = None
        for _fuel in fuel_ui.value:
            _bar.update(subtitle=_fuel)
            _data = pd.read_csv(datadir / _fuel, index_col=[0], parse_dates=[0]).sort_index()
            if data is None:
                data = _data
            else:
                data += _data
        if data is not None:
            data = data.round(3)
        else:
            data = pd.DataFrame()
    return (data,)


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
