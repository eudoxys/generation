"""Dispatchable generation

The `Dispatchable` data frame combines the hourly net generation of all the
dispatchable generation categories in a county:

  - `generation.coal.Coal`
  - `generation.natural_gas.NaturalGas`
  - `generation.oil.Oil`
  - `generation.nuclear.Nuclear`
  - `generation.hydro.Hydro`
  - `generation.geothermal.Geothermal`
  - `generation.biomass.Biomass`
  - `generation.battery_storage.BatteryStorage`
  - `generation.pumped_storage.PumpedStorage`
  - `generation.other.Other`

Example
-------

To get the dispatchable generation in Kern County CA in 2020 use

    from generation.dispatchable import Dispatchable
    Dispatchable("CA","Kern",2020)

which returns 8784 hourly rows with the columns `coal_MW`, `natural_gas_MW`,
`oil_MW`, `nuclear_MW`, `hydro_MW`, `geothermal_MW`, `biomass_MW`,
`battery_storage_MW`, `pumped_storage_MW`, `other_MW`, and the total
`dispatchable_MW`.
"""

from generation.category import Combination
from generation.coal import Coal
from generation.natural_gas import NaturalGas
from generation.oil import Oil
from generation.nuclear import Nuclear
from generation.hydro import Hydro
from generation.geothermal import Geothermal
from generation.biomass import Biomass
from generation.battery_storage import BatteryStorage
from generation.pumped_storage import PumpedStorage
from generation.other import Other

class Dispatchable(Combination):
    """Dispatchable generation data frame

    Columns
    -------

      - `{category}_MW`: total net generation of each dispatchable category

      - `dispatchable_MW`: total dispatchable net generation
    """

    PARTS = [Coal,NaturalGas,Oil,Nuclear,Hydro,Geothermal,Biomass,
        BatteryStorage,PumpedStorage,Other]
    """Dispatchable generation categories"""

    COLUMN = "dispatchable_MW"
    """Total column name"""

if __name__ == "__main__":

    print(Dispatchable("CA","Kern",2020))
