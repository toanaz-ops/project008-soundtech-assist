# PyInstaller spec for the desktop app.
#
# Build from the repository root:
#     pyinstaller packaging\wing-ui.spec --noconfirm
#
# Two things here are load-bearing and easy to get wrong:
#
# 1. Every YAML the package reads is located with Path(__file__), so it
#    must land at the same relative position inside the bundle. Losing
#    one of them does not fail at start-up -- it fails when a rule file
#    is missing and the advisory quietly evaluates fewer rules.
#
# 2. `knowledge/toanaz` is bundled as the *starting set only*.
#    config._REPO_DEFAULT resolves to it inside the bundle, and the
#    bundle is deleted when the process exits, so config.knowledge_dir()
#    deliberately refuses to resolve there when frozen. It resolves to
#    a real per-user directory instead, and config.seed_user_dir()
#    copies this bundled set across on first run. Without that, every
#    verdict the operator recorded would vanish on close.

from PyInstaller.utils.hooks import collect_submodules

import os

# A bare ".." in pathex resolves against the CURRENT DIRECTORY at
# build time, not the spec directory, so it silently ships an exe
# without wing_parser in it. Anchor on SPECPATH (where this spec
# lives) instead.
PATH_TO_REPO_ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))

DATAS = [
    ("../wing_parser/advisory/base_rules", "wing_parser/advisory/base_rules"),
    ("../wing_parser/classifier/data", "wing_parser/classifier/data"),
    ("../wing_parser/descriptors/data", "wing_parser/descriptors/data"),
    ("../wing_parser/edit/data", "wing_parser/edit/data"),
    # What the Console page reads once it is talking to a real desk.
    # Both load lazily (an lru_cache on first call), so a missing one
    # costs nothing at start-up and nothing during a screenshot run --
    # it surfaces only at a venue, on the first Discover or Snapshot
    # against a live console, which is the worst place to find it.
    # net/watch/data/watchlist.yaml -> net/watch/list.py:29, the keys
    # build_watch_list polls; net/data/wing_jsontypes.yaml ->
    # net/jsontypes.py:28, which leaves a snapshot writes as JSON
    # booleans. ui/live_controller.py:30,34 reaches both.
    ("../wing_parser/net/data", "wing_parser/net/data"),
    ("../wing_parser/net/watch/data", "wing_parser/net/watch/data"),
    # Theme resources (qss templates, vendored fonts, licences).
    # resource_path() maps this directory to the same relative position
    # in dev and under sys._MEIPASS, so one entry serves both.
    ("../wing_parser/ui/resources", "wing_parser/ui/resources"),
    # The seed. Target path must match config._REPO_DEFAULT, which is
    # <bundle root>/knowledge/toanaz.
    ("../knowledge/toanaz", "knowledge/toanaz"),
]

# Optional extras this build deliberately does not carry. The tool is
# for venues where the network is unreliable or absent, but Settings
# does perform user-initiated provider calls (the Test connection
# button), so the anthropic SDK is NOT excluded -- only mcp, pytest
# and the web engine are.
EXCLUDES = ["mcp", "pytest", "PySide6.QtWebEngineCore"]

analysis = Analysis(
    ["wing-ui.py"],
    pathex=[PATH_TO_REPO_ROOT],
    datas=DATAS,
    hiddenimports=collect_submodules("wing_parser") + ["qtawesome"],
    excludes=EXCLUDES,
    noarchive=False,
)

pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name="wing-ui",
    console=False,
    upx=False,
    strip=False,
)
