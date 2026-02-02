"""Generation fleet data accessor

Modules
-------

- `generation.cli`: Command line interface

- `generation.generation`: Generation data accessor

Package information
-------------------

  - Source code: https://github.com/eudoxys/generation

  - Documentation: https://www.eudoxys.com/generation

  - Issues: https://github.com/eudoxys/generation/issues

  - License: https://github.com/eudoxys/generation/blob/main/LICENSE

  - Dependencies: 

    - [pandas](https://pypi.org/project/pandas/)
    - [eia](https://github.com/eudoxys/eia/)
"""

from generation.generation import Generation
from generation.cli import main
