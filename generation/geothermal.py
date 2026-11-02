"""Geothermal generation

The `Geothermal` data frame contains the hourly net generation of geothermal steam and binary cycle turbines in a
county. This is dispatchable generation (see `generation.dispatchable`).

Monthly plant net generation from EIA Form 923 is shaped into hours using
a flat profile within each month. See `generation.category` for the method and caveats.

Example
-------

To get the geothermal generation in Kern County CA in 2020 use

    from generation.geothermal import Geothermal
    Geothermal("CA","Kern",2020)

which returns 8784 hourly rows with one `plant_{id}_MW` column for each
contributing plant and the total `geothermal_MW` column.
"""

from generation.category import Category

class Geothermal(Category):
    """Geothermal generation data frame

    Columns
    -------

      - `plant_{id}_MW`: net generation of EIA plant `id`

      - `geothermal_MW`: total geothermal generation in the county
    """

    CATEGORY = "geothermal"
    """Generation category"""

if __name__ == "__main__":

    print(Geothermal("CA","Kern",2020))
