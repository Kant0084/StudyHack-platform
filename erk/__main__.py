"""支持通过 `python -m erk` 运行 CLI。"""

import sys

from erk.cli import main

if __name__ == "__main__":
    sys.exit(main())
