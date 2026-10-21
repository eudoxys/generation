"""Conventional hydroelectric generation

The `Hydro` data frame contains the hourly net generation of conventional hydroelectric turbines (pumped storage is `generation.pumped_storage`) in a
county. This is dispatchable generation (see `generation.dispatchable`).

Monthly plant net generation from EIA Form 923 is shaped into hours using
the balancing authority's Form 930 `WAT` net generation. See `generation.category` for the method and caveats.

Example
-------

To get the conventional hydroelectric generation in Kern County CA in 2020 use

    from generation.hydro import Hydro
    Hydro("CA","Kern",2020)

which returns 8784 hourly rows with one `plant_{id}_MW` column for each
contributing plant and the total `hydro_MW` column.
"""

from generation.category import Category

class Hydro(Category):
    """Conventional hydroelectric generation data frame

    Columns
    -------

      - `plant_{id}_MW`: net generation of EIA plant `id`

      - `hydro_MW`: total conventional hydroelectric generation in the county
    """

    CATEGORY = "hydro"
    """Generation category"""

if __name__ == "__main__":

    print(Hydro("CA","Kern",2020))
