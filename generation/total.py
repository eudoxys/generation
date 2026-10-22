"""Total generation

The `Total` data frame combines the dispatchable
(`generation.dispatchable.Dispatchable`) and non-dispatchable
(`generation.nondispatchable.Nondispatchable`) generation in a county.

```mermaid
flowchart LR
    Coal --> Dispatchable
    NaturalGas --> Dispatchable
    Oil --> Dispatchable
    Nuclear --> Dispatchable
    Hydro --> Dispatchable
    Geothermal --> Dispatchable
    Biomass --> Dispatchable
    BatteryStorage --> Dispatchable
    PumpedStorage --> Dispatchable
    Other --> Dispatchable
    Solar --> Nondispatchable
    Wind --> Nondispatchable
    Dispatchable --> Total
    Nondispatchable --> Total
```

Example
-------

To get the total generation in Kern County CA in 2020 use

    from generation import Total
    Total("CA","Kern",2020)

which returns 8784 hourly rows with the columns of `Dispatchable`
(`coal_MW` through `other_MW`, and `dispatchable_MW`), the columns of
`Nondispatchable` (`solar_MW`, `wind_MW`, and `nondispatchable_MW`), and
`total_MW`, where

    total_MW = dispatchable_MW + nondispatchable_MW
"""

from generation.category import Combination
from generation.dispatchable import Dispatchable
from generation.nondispatchable import Nondispatchable

class Total(Combination):
    """Total generation data frame

    Columns
    -------

      - `{category}_MW`: total net generation of each category

      - `dispatchable_MW`: total dispatchable net generation

      - `nondispatchable_MW`: total non-dispatchable net generation

      - `total_MW`: total net generation
    """

    PARTS = [Dispatchable,Nondispatchable]
    """Generation data frames combined"""

    COLUMN = "total_MW"
    """Total column name"""

if __name__ == "__main__":

    print(Total("CA","Kern",2020))
