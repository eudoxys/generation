"""Wind generation

The `Wind` data frame contains the hourly net generation of onshore and offshore wind turbines in a
county. This is non-dispatchable generation (see `generation.nondispatchable`).

Monthly plant net generation from EIA Form 923 is shaped into hours using
the balancing authority's Form 930 `WND` net generation. See `generation.category` for the method and caveats.

Example
-------

To get the wind generation in Kern County CA in 2020 use

    from generation.wind import Wind
    Wind("CA","Kern",2020)

which returns 8784 hourly rows with one `plant_{id}_MW` column for each
contributing plant and the total `wind_MW` column.
"""

from generation.category import Category

class Wind(Category):
    """Wind generation data frame

    Columns
    -------

      - `plant_{id}_MW`: net generation of EIA plant `id`

      - `wind_MW`: total wind generation in the county
    """

    CATEGORY = "wind"
    """Generation category"""

if __name__ == "__main__":

    print(Wind("CA","Kern",2020))
