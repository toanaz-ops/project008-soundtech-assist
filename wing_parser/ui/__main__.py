"""Boot the application. Argument wiring and nothing else.

PySide6 is imported inside `main()` rather than at module scope, for
two reasons: a missing GUI extra then produces one line naming the
install command instead of an ImportError traceback, and importing
this module costs nothing when Qt is not wanted.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

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
        "--screenshot",
        nargs="?",
        const="screenshots",
        metavar="DIR",
        help="grab one PNG per page and exit",
    )
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
        from PySide6.QtGui import QImage
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

    from wing_parser.ui.main_window import PAGE_ORDER, MainWindow
    from wing_parser.ui.theme import apply as apply_theme

    if args.screenshot:
        # Qt reads these at QApplication construction, not later -- so
        # they must be set before the line below, never after.
        os.environ.setdefault("QT_SCALE_FACTOR", "1")
        os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "0")

    # Qt permits exactly one QApplication per process, and constructing
    # a second raises. Reusing an existing one is what lets this
    # function be called from a test process that already has one.
    application = QApplication.instance() or QApplication(sys.argv[:1])
    apply_theme(application)

    window = MainWindow(session)
    window.show()
    if args.screenshot:
        # Fixed frame so grabs compare across machines and DPI settings.
        window.setFixedSize(1280, 760)
        directory = Path(args.screenshot)
        directory.mkdir(parents=True, exist_ok=True)
        for key in PAGE_ORDER:
            window.switch_to(key)
            if key == "diff" and window.session is not None:
                # A/B review artifact: seed the diff table (live scene
                # vs a fader-nudged copy) so the magnitude bar has rows.
                from wing_parser.ui import diff_page
                window.pages["diff"].compare_with(
                    str(diff_page.seeded_other(window.session, directory))
                )
            QApplication.processEvents()
            # Render straight into a 1:1 image rather than grab(): a
            # host that built QApplication before the pins above (a
            # test process sharing one app) grabs at the display's
            # device pixel ratio, and resampling those pixels back to
            # 1280x760 blurs every glyph off its exact token colour.
            frame = QImage(1280, 760, QImage.Format.Format_ARGB32_Premultiplied)
            window.render(frame)
            frame.save(str(directory / f"{key}.png"))
            if key == "diff":
                # A/B review artifact: the same frame with the magnitude
                # bar forced off, so ToanAZ can judge the option.
                from wing_parser.ui import diff_page
                diff_page.SHOW_MAGNITUDE_BAR = False
                window.render(frame)
                frame.save(str(directory / "diff-b.png"))
                diff_page.SHOW_MAGNITUDE_BAR = True
        return 0
    return application.exec()


if __name__ == "__main__":
    sys.exit(main())
