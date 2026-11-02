"""Natural gas generation

The `NaturalGas` data frame contains the hourly net generation of natural gas in combustion turbines, combined cycles, steam turbines and reciprocating engines in a
county. This is dispatchable generation (see `generation.dispatchable`).

Monthly plant net generation from EIA Form 923 is shaped into hours using
the balancing authority's Form 930 `NG` net generation. See `generation.category` for the method and caveats.

Example
-------

To get the natural gas generation in Kern County CA in 2020 use

    from generation.natural_gas import NaturalGas
    NaturalGas("CA","Kern",2020)

which returns 8784 hourly rows with one `plant_{id}_MW` column for each
contributing plant and the total `natural_gas_MW` column.
"""

from generation.category import Category

class NaturalGas(Category):
    """Natural gas generation data frame

    Columns
    -------

      - `plant_{id}_MW`: net generation of EIA plant `id`

      - `natural_gas_MW`: total natural gas generation in the county
    """

    CATEGORY = "natural_gas"
    """Generation category"""

if __name__ == "__main__":

    print(NaturalGas("CA","Kern",2020))
