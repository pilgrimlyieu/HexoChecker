"""Package entry point for python -m checks"""

import sys

from checks.cli import main

if __name__ == "__main__":
    sys.exit(main())
