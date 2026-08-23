"""Entry script for the frozen build.

PyInstaller wants a script, not a module, and the name of that script
becomes the default name of the executable. This exists so the exe is
called `wing-ui` and so the spec has one obvious thing to point at; it
holds no behaviour of its own.
"""

import sys

from wing_parser.ui.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
