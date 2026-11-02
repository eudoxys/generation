"""Generation fleet data accessor

Hourly, county-level models of US utility-scale generation assembled from
EIA public data. See `DESIGN.md` in the source repository for the package
design.

All generation data frames are constructed as `Class(state,county,year)` and
return the hourly net generation (MW) of the county, indexed by UTC
hour-beginning `timestamp`.

Modules
-------

- `generation.cli`: Command line interface

- `generation.fleet`: Generator fleet inventory (EIA Form 860m)

- `generation.fuels`: Energy source codes and generation categories

- `generation.category`: Generation data frame base classes and method

- `generation.total`: Total generation (dispatchable and non-dispatchable)

- `generation.dispatchable`: Dispatchable generation

  - `generation.coal`: Coal generation

  - `generation.natural_gas`: Natural gas generation

  - `generation.oil`: Oil generation

  - `generation.nuclear`: Nuclear generation

  - `generation.hydro`: Conventional hydroelectric generation

  - `generation.geothermal`: Geothermal generation

  - `generation.biomass`: Biomass generation

  - `generation.battery_storage`: Battery storage net generation

  - `generation.pumped_storage`: Pumped storage net generation

  - `generation.other`: Other generation

- `generation.nondispatchable`: Non-dispatchable generation

  - `generation.solar`: Utility-scale solar generation

  - `generation.wind`: Wind generation

Package information
-------------------

  - Source code: https://github.com/eudoxys/generation

  - Documentation: https://www.eudoxys.com/generation

  - Issues: https://github.com/eudoxys/generation/issues

  - License: https://github.com/eudoxys/generation/blob/main/LICENSE

  - Dependencies: 

    - [pandas](https://pypi.org/project/pandas/)
    - [eia](https://github.com/eudoxys/eia/)
    - [cache](https://github.com/eudoxys/cache/)
    - [geohash](https://github.com/eudoxys/geohash/)
    - [numpy](https://pypi.org/project/numpy/)
"""

from generation.fleet import Fleet
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
from generation.solar import Solar
from generation.wind import Wind
from generation.dispatchable import Dispatchable
from generation.nondispatchable import Nondispatchable
from generation.total import Total
from generation.cli import main
