"""Coal-fired generation

The `Coal` data frame contains the hourly net generation of anthracite, bituminous, subbituminous and lignite coal, waste and refined coal, and coal-derived synthesis gas in a
county. This is dispatchable generation (see `generation.dispatchable`).

Monthly plant net generation from EIA Form 923 is shaped into hours using
the balancing authority's Form 930 `COL` net generation. See `generation.category` for the method and caveats.

Example
-------

To get the coal-fired generation in Kern County CA in 2020 use

    from generation.coal import Coal
    Coal("CA","Kern",2020)

which returns 8784 hourly rows with one `plant_{id}_MW` column for each
contributing plant and the total `coal_MW` column.
"""

from generation.category import Category

class Coal(Category):
    """Coal-fired generation data frame

    Columns
    -------

      - `plant_{id}_MW`: net generation of EIA plant `id`

      - `coal_MW`: total coal-fired generation in the county
    """

    CATEGORY = "coal"
    """Generation category"""

if __name__ == "__main__":

    print(Coal("CA","Kern",2020))
