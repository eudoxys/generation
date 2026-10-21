"""Energy source categories

Maps EIA energy source codes (Form 860m `fuel` and Form 923 reported fuel
type) and prime mover codes to the 12 generation categories used by this
package, and gives the EIA Form 930 energy source code used to shape each
category's monthly energy into hours.

Categories
----------

| category | module | dispatchable | Form 930 shape |
|---|---|---|---|
| `coal` | `generation.coal` | yes | `COL` |
| `natural_gas` | `generation.natural_gas` | yes | `NG` |
| `oil` | `generation.oil` | yes | `OIL` |
| `nuclear` | `generation.nuclear` | yes | `NUC` |
| `hydro` | `generation.hydro` | yes | `WAT` |
| `geothermal` | `generation.geothermal` | yes | flat |
| `biomass` | `generation.biomass` | yes | flat |
| `battery_storage` | `generation.battery_storage` | yes | `BAT` |
| `pumped_storage` | `generation.pumped_storage` | yes | `PS` |
| `other` | `generation.other` | yes | `OTH` |
| `solar` | `generation.solar` | no | `SUN` |
| `wind` | `generation.wind` | no | `WND` |

Example
-------

    from generation.fuels import category
    category("SUB","ST")

returns `"coal"`.
"""

CATEGORIES = [
    "coal",
    "natural_gas",
    "oil",
    "nuclear",
    "hydro",
    "geothermal",
    "biomass",
    "battery_storage",
    "pumped_storage",
    "other",
    "solar",
    "wind",
    ]
"""Generation categories"""

DISPATCHABLE = [x for x in CATEGORIES if x not in ("solar","wind")]
"""Dispatchable generation categories"""

NONDISPATCHABLE = ["solar","wind"]
"""Non-dispatchable generation categories"""

FUELS = {
    # coal, including coal-derived synthesis gas
    "ANT": "coal",
    "BIT": "coal",
    "LIG": "coal",
    "SUB": "coal",
    "SGC": "coal",
    "WC": "coal",
    "RC": "coal",
    "SC": "coal",
    # natural gas
    "NG": "natural_gas",
    # petroleum liquids and petroleum coke
    "DFO": "oil",
    "RFO": "oil",
    "JF": "oil",
    "KER": "oil",
    "WO": "oil",
    "PC": "oil",
    # nuclear
    "NUC": "nuclear",
    # conventional hydro (pumped storage is identified by prime mover)
    "WAT": "hydro",
    # geothermal
    "GEO": "geothermal",
    # biomass
    "AB": "biomass",
    "BLQ": "biomass",
    "LFG": "biomass",
    "MSB": "biomass",
    "MSW": "biomass",
    "OBG": "biomass",
    "OBL": "biomass",
    "OBS": "biomass",
    "SLW": "biomass",
    "WDL": "biomass",
    "WDS": "biomass",
    # storage (also identified by prime mover)
    "MWH": "battery_storage",
    # non-dispatchable
    "SUN": "solar",
    "WND": "wind",
    }
"""EIA energy source code to category (codes not listed are `other`)"""

PRIME_MOVERS = {
    "PS": "pumped_storage",
    "BA": "battery_storage",
    "CE": "battery_storage",
    "FW": "battery_storage",
    "ES": "battery_storage",
    }
"""EIA prime mover codes that determine the category regardless of fuel"""

SHAPES = {
    "coal": "COL",
    "natural_gas": "NG",
    "oil": "OIL",
    "nuclear": "NUC",
    "hydro": "WAT",
    "geothermal": None,
    "biomass": None,
    "battery_storage": "BAT",
    "pumped_storage": "PS",
    "other": "OTH",
    "solar": "SUN",
    "wind": "WND",
    }
"""Form 930 energy source code used to shape each category (`None` is flat)"""

def category(fuel:str,pm:str|None=None) -> str:
    """Get the generation category of an energy source and prime mover

    Arguments
    ---------

      - `fuel`: EIA energy source code (e.g., `"NG"`)

      - `pm`: EIA prime mover code (e.g., `"CT"`)

    Returns
    -------

      - `str`: one of `CATEGORIES`
    """
    if isinstance(pm,str) and pm.strip().upper() in PRIME_MOVERS:
        return PRIME_MOVERS[pm.strip().upper()]
    if isinstance(fuel,str):
        return FUELS.get(fuel.strip().upper(),"other")
    return "other"
