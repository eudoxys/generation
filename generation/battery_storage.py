"""Battery storage net generation

The `BatteryStorage` data frame contains the hourly net generation of batteries, flywheels and other energy storage (except pumped storage); net generation is negative when charging and losses exceed discharge in a
county. This is dispatchable generation (see `generation.dispatchable`).

Monthly plant net generation from EIA Form 923 is shaped into hours using
the balancing authority's Form 930 `BAT` net generation. See `generation.category` for the method and caveats.

Example
-------

To get the battery storage net generation in Kern County CA in 2020 use

    from generation.battery_storage import BatteryStorage
    BatteryStorage("CA","Kern",2020)

which returns 8784 hourly rows with one `plant_{id}_MW` column for each
contributing plant and the total `battery_storage_MW` column.
"""

from generation.category import Category

class BatteryStorage(Category):
    """Battery storage net generation data frame

    Columns
    -------

      - `plant_{id}_MW`: net generation of EIA plant `id`

      - `battery_storage_MW`: total battery storage net generation in the county
    """

    CATEGORY = "battery_storage"
    """Generation category"""

if __name__ == "__main__":

    print(BatteryStorage("CA","Kern",2020))
