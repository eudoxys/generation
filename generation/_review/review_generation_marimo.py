import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    This notebook allows you to review the hourly total generation data (`generation.total.Total`) for individual counties.

    Choose a year, state, and county. Only counties with operating generators in December of the chosen year (EIA Form 860m) are listed.
    """)
    return


@app.cell
def _(dt, mo):
    _years = list(range(2018,dt.datetime.now().year))
    year_ui = mo.ui.dropdown(options={str(x):x for x in _years},value=str(_years[-1]),label="Year")
    return (year_ui,)


@app.cell
def _(Fleet, mo, year_ui):
    year = year_ui.value
    with mo.status.spinner("Reading generator fleet"):
        fleet = Fleet(year=year,months=12).reset_index()
    fleet = fleet[fleet["county"].notna()]
    states = sorted(fleet["state"].unique().tolist())
    state_counties = {x:sorted(fleet.loc[fleet["state"]==x,"county"].unique().tolist()) for x in states}
    return fleet, state_counties, states, year


@app.cell
def _(mo, states):
    state_ui = mo.ui.dropdown(options=states,value="CA" if "CA" in states else states[0],label="State")
    return (state_ui,)


@app.cell
def _(mo, state_counties, state_ui):
    state = state_ui.value
    _options = state_counties[state]
    county_ui = mo.ui.dropdown(options=_options,value=_options[0],label="County")
    return county_ui, state


@app.cell
def _(county_ui, mo, state_ui, year_ui):
    refresh_ui = mo.ui.checkbox(label="Refresh cache")
    mo.hstack([year_ui,state_ui,county_ui,refresh_ui],justify="start")
    return (refresh_ui,)


@app.cell
def _(Total, county_ui, mo, refresh_ui, state, year):
    county = county_ui.value
    with mo.status.spinner(f"Computing generation in {county} {state} in {year}"):
        data = Total(state,county,year,refresh=refresh_ui.value)
    return county, data


@app.cell
def _(data):
    # categories are the columns that are not subtotals or the total
    TOTALS = ["dispatchable_MW","nondispatchable_MW","total_MW"]
    categories = [x for x in data.columns if x not in TOTALS]
    present = [x for x in categories if (data[x] != 0).any()]
    return TOTALS, categories, present


@app.cell
def _(county, data, fleet, mo, present, state):
    _plants = fleet[(fleet["state"]==state) & (fleet["county"]==county)]
    _hours = len(data)
    mo.hstack([
        mo.stat(f"{data['total_MW'].sum()/1e3:,.1f} GWh",label="Net generation"),
        mo.stat(f"{data['total_MW'].max():,.1f} MW",label="Peak hourly"),
        mo.stat(f"{data['total_MW'].mean():,.1f} MW",label="Mean hourly"),
        mo.stat(f"{_plants['nameplate_MW'].sum():,.1f} MW",label="Nameplate (Dec)"),
        mo.stat(f"{_plants['id'].nunique()}",label="Plants (Dec)"),
        mo.stat(f"{len(present)}",label="Categories present"),
        ],justify="start")
    return


@app.cell
def _(TOTALS, categories, data, pd):
    # summary statistics by column
    summary = pd.DataFrame({
        "energy_GWh": data.sum()/1e3,
        "mean_MW": data.mean(),
        "min_MW": data.min(),
        "max_MW": data.max(),
        })
    _total = summary.loc["total_MW","energy_GWh"]
    summary["share_pc"] = 100*summary["energy_GWh"]/_total if _total != 0 else float("nan")
    summary = summary.loc[categories+TOTALS].round(3)
    return (summary,)


@app.cell
def _(data, mo, present):
    _months = sorted(set(data.index.month))
    month_ui = mo.ui.range_slider(start=_months[0],stop=_months[-1],step=1,
        value=[_months[0],_months[-1]],label="Months",show_value=True)
    columns_ui = mo.ui.multiselect(options=present,value=present,label="Categories")
    mo.hstack([month_ui,columns_ui],justify="start")
    return columns_ui, month_ui


@app.cell
def _(columns_ui, data, month_ui):
    _start,_stop = month_ui.value
    view = data.loc[(data.index.month >= _start) & (data.index.month <= _stop)]
    shown = list(columns_ui.value)
    return shown, view


@app.cell
def _(county, plt, shown, state, view, year):
    def hourly_plot():
        """Stacked hourly generation; signed categories (e.g., storage) are lines"""
        fig,ax = plt.subplots(figsize=(12,5))
        stacked = [x for x in shown if view[x].min() >= 0]
        signed = [x for x in shown if view[x].min() < 0]
        if stacked:
            ax.stackplot(view.index,*[view[x] for x in stacked],labels=stacked,alpha=0.8)
        for x in signed:
            ax.plot(view.index,view[x],label=x,linewidth=0.8)
        ax.plot(view.index,view["total_MW"],color="black",linewidth=0.6,label="total_MW")
        ax.axhline(0,color="grey",linewidth=0.5)
        ax.set_ylabel("Net generation (MW)")
        ax.set_title(f"{county} {state} {year} hourly net generation")
        ax.legend(loc="upper left",bbox_to_anchor=(1.01,1),fontsize="small")
        ax.grid(alpha=0.3)
        fig.tight_layout()
        return fig
    hourly_plot()
    return


@app.cell
def _(county, plt, shown, state, view, year):
    def monthly_plot():
        """Monthly energy by category"""
        monthly = view[shown or ["total_MW"]].groupby(view.index.month).sum()/1e3
        fig,ax = plt.subplots(figsize=(12,4))
        monthly.plot.bar(ax=ax,stacked=True,width=0.8)
        ax.set_xlabel("Month")
        ax.set_ylabel("Net generation (GWh)")
        ax.set_title(f"{county} {state} {year} monthly net generation")
        ax.legend(loc="upper left",bbox_to_anchor=(1.01,1),fontsize="small")
        ax.grid(alpha=0.3,axis="y")
        fig.tight_layout()
        return fig
    monthly_plot()
    return


@app.cell
def _(county, plt, shown, state, view, year):
    def profile_plot():
        """Average hour-of-day profile (UTC) by category"""
        profile = view[shown+["total_MW"]].groupby(view.index.hour).mean()
        fig,ax = plt.subplots(figsize=(12,4))
        profile.plot(ax=ax,marker=".")
        ax.set_xlabel("Hour of day (UTC)")
        ax.set_ylabel("Mean net generation (MW)")
        ax.set_xticks(range(0,24,2))
        ax.set_title(f"{county} {state} {year} average daily profile")
        ax.legend(loc="upper left",bbox_to_anchor=(1.01,1),fontsize="small")
        ax.grid(alpha=0.3)
        fig.tight_layout()
        return fig
    profile_plot()
    return


@app.cell
def _(data, mo, summary):
    mo.ui.tabs({
        "Summary": mo.ui.table(summary.reset_index(names="column"),selection=None),
        "Hourly data": mo.ui.table(data.reset_index(),selection=None,page_size=24),
        })
    return


@app.cell
def _():
    import marimo as mo
    import datetime as dt
    import pandas as pd
    import matplotlib.pyplot as plt
    from generation.fleet import Fleet
    from generation.total import Total

    return Fleet, Total, dt, mo, pd, plt


if __name__ == "__main__":
    app.run()
