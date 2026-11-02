"""Other generation

The `Other` data frame contains the hourly net generation of all other energy sources, e.g., other gases, purchased steam, waste heat, tire-derived fuel, non-biogenic municipal solid waste and hydrogen in a
county. This is dispatchable generation (see `generation.dispatchable`).

Monthly plant net generation from EIA Form 923 is shaped into hours using
the balancing authority's Form 930 `OTH` net generation. See `generation.category` for the method and caveats.

Example
-------

To get the other generation in Kern County CA in 2020 use

    from generation.other import Other
    Other("CA","Kern",2020)

which returns 8784 hourly rows with one `plant_{id}_MW` column for each
contributing plant and the total `other_MW` column.
"""

from generation.category import Category

class Other(Category):
    """Other generation data frame

    Columns
    -------

      - `plant_{id}_MW`: net generation of EIA plant `id`

      - `other_MW`: total other generation in the county
    """

    CATEGORY = "other"
    """Generation category"""

if __name__ == "__main__":

    print(Other("CA","Kern",2020))
