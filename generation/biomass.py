"""Biomass generation

The `Biomass` data frame contains the hourly net generation of wood and wood waste, black liquor, agricultural byproducts, municipal solid waste (biogenic), landfill gas and other biomass in a
county. This is dispatchable generation (see `generation.dispatchable`).

Monthly plant net generation from EIA Form 923 is shaped into hours using
a flat profile within each month. See `generation.category` for the method and caveats.

Example
-------

To get the biomass generation in Kern County CA in 2020 use

    from generation.biomass import Biomass
    Biomass("CA","Kern",2020)

which returns 8784 hourly rows with one `plant_{id}_MW` column for each
contributing plant and the total `biomass_MW` column.
"""

from generation.category import Category

class Biomass(Category):
    """Biomass generation data frame

    Columns
    -------

      - `plant_{id}_MW`: net generation of EIA plant `id`

      - `biomass_MW`: total biomass generation in the county
    """

    CATEGORY = "biomass"
    """Generation category"""

if __name__ == "__main__":

    print(Biomass("CA","Kern",2020))
