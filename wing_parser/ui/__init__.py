"""The desktop application.

Most of this package holds widgets, but "only session.py is Qt-free" was
already false before wave 2 (`data.py`, `state_store.py`, `texts.py` and
`import_controller.py` carry no `PySide6` import either) and wave 2 added
four more: `live_controller.py`, `live_guard.py`, `live_state.py` and
`live_wiring.py`. As of 2026-09-16 the non-Qt modules (no `PySide6`
import anywhere in the file -- `rg -L "PySide6" wing_parser/ui/*.py`) are
`session.py`, `state_store.py`, `data.py`, `texts.py`, `texts_console.py`,
`import_controller.py`, `live_controller.py`, `live_guard.py`,
`live_state.py` and `live_wiring.py`. The dependency still runs one way
-- the window observes the session, never the reverse -- which is what
keeps every decision the application makes testable without a display.

PySide6 is the optional `ui` extra. The engine and the CLI must keep
working with no GUI installed at all.
"""
