"""Non-dispatchable generation

The `Nondispatchable` data frame combines the hourly net generation of the
non-dispatchable generation categories in a county:

  - `generation.solar.Solar`
  - `generation.wind.Wind`

Example
-------

To get the non-dispatchable generation in Kern County CA in 2020 use

    from generation.nondispatchable import Nondispatchable
    Nondispatchable("CA","Kern",2020)

which returns 8784 hourly rows with the columns `solar_MW`, `wind_MW`, and
the total `nondispatchable_MW`.
"""

from generation.category import Combination
from generation.solar import Solar
from generation.wind import Wind

class Nondispatchable(Combination):
    """Non-dispatchable generation data frame

    Columns
    -------

      - `solar_MW`: total utility-scale solar net generation

      - `wind_MW`: total wind net generation

      - `nondispatchable_MW`: total non-dispatchable net generation
    """

    PARTS = [Solar,Wind]
    """Non-dispatchable generation categories"""

    COLUMN = "nondispatchable_MW"
    """Total column name"""

if __name__ == "__main__":

    print(Nondispatchable("CA","Kern",2020))
