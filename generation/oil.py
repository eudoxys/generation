"""Oil-fired generation

The `Oil` data frame contains the hourly net generation of distillate and residual fuel oil, jet fuel, kerosene, waste oil and petroleum coke in a
county. This is dispatchable generation (see `generation.dispatchable`).

Monthly plant net generation from EIA Form 923 is shaped into hours using
the balancing authority's Form 930 `OIL` net generation. See `generation.category` for the method and caveats.

Example
-------

To get the oil-fired generation in Kern County CA in 2020 use

    from generation.oil import Oil
    Oil("CA","Kern",2020)

which returns 8784 hourly rows with one `plant_{id}_MW` column for each
contributing plant and the total `oil_MW` column.
"""

from generation.category import Category

class Oil(Category):
    """Oil-fired generation data frame

    Columns
    -------

      - `plant_{id}_MW`: net generation of EIA plant `id`

      - `oil_MW`: total oil-fired generation in the county
    """

    CATEGORY = "oil"
    """Generation category"""

if __name__ == "__main__":

    print(Oil("CA","Kern",2020))
