"""Utility-scale solar generation

The `Solar` data frame contains the hourly net generation of utility-scale photovoltaic and solar thermal plants (rooftop PV is not included) in a
county. This is non-dispatchable generation (see `generation.nondispatchable`).

Monthly plant net generation from EIA Form 923 is shaped into hours using
the balancing authority's Form 930 `SUN` net generation. See `generation.category` for the method and caveats.

Example
-------

To get the utility-scale solar generation in Kern County CA in 2020 use

    from generation.solar import Solar
    Solar("CA","Kern",2020)

which returns 8784 hourly rows with one `plant_{id}_MW` column for each
contributing plant and the total `solar_MW` column.
"""

from generation.category import Category

class Solar(Category):
    """Utility-scale solar generation data frame

    Columns
    -------

      - `plant_{id}_MW`: net generation of EIA plant `id`

      - `solar_MW`: total utility-scale solar generation in the county
    """

    CATEGORY = "solar"
    """Generation category"""

if __name__ == "__main__":

    print(Solar("CA","Kern",2020))
