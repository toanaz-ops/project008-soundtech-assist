"""Boot the application. Argument wiring and nothing else.

PySide6 is imported inside `main()` rather than at module scope, for
two reasons: a missing GUI extra then produces one line naming the
install command instead of an ImportError traceback, and importing
this module costs nothing when Qt is not wanted.
"""

from __future__ import annotations

import argparse
import sys

from wing_parser import config

MISSING_PYSIDE = (
    'error: the desktop app needs PySide6, which is an optional extra.\n'
    '       Install it with:  pip install -e ".[ui]"'
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="wing-ui", description="Open a WING .snap scene in the desktop app"
    )
    parser.add_argument("file", nargs="?", help="a .snap scene to open on start")
    parser.add_argument(
        "--profile",
        default=None,
        help="apply one show profile from knowledge/toanaz/shows/<name>.yaml",
    )
    args = parser.parse_args(argv)

    # Before anything reads or writes it. In a packaged build the
    # knowledge directory resolves to a real per-user path that starts
    # out empty, and this copies the shipped principles and show
    # profiles into it once. A no-op for a normal run from the repo,
    # and a no-op on every run after the first.
    #
    # Deliberately silent: a frozen build is windowed, so anything
    # printed here goes nowhere on Windows. The window's Help menu
    # names the directory instead, which is useful on every run rather
    # than only the first.
    config.seed_user_dir()

    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print(MISSING_PYSIDE, file=sys.stderr)
        return 1

    from wing_parser.ui.session import Session

    # Load before building any GUI. Refusing on the command line beats
    # opening an empty window that gives no hint why the file named on
    # it is not in it -- and a bad path then costs no Qt startup at all.
    try:
        session = Session.open(args.file, args.profile) if args.file else None
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    from wing_parser.ui.main_window import MainWindow

    # Qt permits exactly one QApplication per process, and constructing
    # a second raises. Reusing an existing one is what lets this
    # function be called from a test process that already has one.
    application = QApplication.instance() or QApplication(sys.argv[:1])

    window = MainWindow(session)
    window.show()
    return application.exec()


if __name__ == "__main__":
    sys.exit(main())
