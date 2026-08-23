"""The desktop application.

Only `session.py` in this package is free of Qt; everything else holds
widgets. The dependency runs one way -- the window observes the
session, never the reverse -- which is what keeps every decision the
application makes testable without a display.

PySide6 is the optional `ui` extra. The engine and the CLI must keep
working with no GUI installed at all.
"""
