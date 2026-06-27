"""Entry point for `python -m anki_poems`."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
