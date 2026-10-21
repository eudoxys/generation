"""Pumped storage net generation

The `PumpedStorage` data frame contains the hourly net generation of pumped storage hydroelectric plants; net generation is usually negative over a month because pumping exceeds generation in a
county. This is dispatchable generation (see `generation.dispatchable`).

Monthly plant net generation from EIA Form 923 is shaped into hours using
the balancing authority's Form 930 `PS` net generation. See `generation.category` for the method and caveats.

Example
-------

To get the pumped storage net generation in Kern County CA in 2020 use

    from generation.pumped_storage import PumpedStorage
    PumpedStorage("CA","Kern",2020)

which returns 8784 hourly rows with one `plant_{id}_MW` column for each
contributing plant and the total `pumped_storage_MW` column.
"""

from generation.category import Category

class PumpedStorage(Category):
    """Pumped storage net generation data frame

    Columns
    -------

      - `plant_{id}_MW`: net generation of EIA plant `id`

      - `pumped_storage_MW`: total pumped storage net generation in the county
    """

    CATEGORY = "pumped_storage"
    """Generation category"""

if __name__ == "__main__":

    print(PumpedStorage("CA","Kern",2020))
