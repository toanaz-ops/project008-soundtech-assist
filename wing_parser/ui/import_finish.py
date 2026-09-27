"""The Import wizard's back half: rebuild, preview, write.

Split out of `import_steps.py` (Task 9 fix round 1) to free headroom
there without changing behaviour -- these four functions are the
step 3 -> 4 -> 5 transitions (`refresh_result`/`show_scene_step`
rebuild against the freshly taught vocabulary and hand off to the
Scene step; `finish_scene` renders the preview; `write_output` is
Save minus the dialog), a cohesive unit separate from step *building*
and *wiring*, which is what remains in `import_steps.py`.
"""

from __future__ import annotations

from pathlib import Path

from wing_parser.ui import import_controller as ic


def refresh_result(page) -> bool:
    """R1: Preview and Save must reflect what Record/Ignore just taught
    in the Terms step, not the mapping-time snapshot -- rebuild from the
    stored read/resolved mapping against the freshly loaded vocabulary at
    this wizard's own directory.

    Returns False, having already reported through `page._fail`, when the
    rebuild itself fails -- fix round 2: the caller must then stop rather
    than show or write the stale `page._result` it never touches on
    failure. Returns True when there is nothing to rebuild (a test that
    hands `show_terms_step` a bare result directly, never having gone
    through `finish_mapping`) or when the rebuild succeeds.
    """
    if page._read is None or page._resolved is None:
        return True
    try:
        page._result = ic.build_result(page._read, page._resolved, page._directory)
    except (OSError, ValueError) as exc:
        page._fail(exc)
        return False
    return True


def show_scene_step(page) -> None:
    """Step 3 -> step 4: rebuild against the freshly taught vocabulary
    (same rule as the old show_preview, R1) and hand the scene step the
    just-built result. A failed rebuild has already reported itself;
    stop here without advancing past step 3 (fix round 2)."""
    if not refresh_result(page):
        return
    page.scene_step.set_result(page._result)
    page.step_area.setCurrentIndex(3)


def finish_scene(page, scene) -> None:
    """Step 4 -> step 5: render the YAML, with the chosen scene's
    cross-check proposals if any -- Skip passes scene=None. I2: this is
    now the ONLY place `ic.preview_text` is called on the way to a saved
    file -- `write_output` writes exactly this rendered text back out,
    never re-renders it."""
    try:
        page.preview_pane.setPlainText(
            ic.preview_text(page._xlsx, page._result, scene=scene)
        )
    except (OSError, ValueError) as exc:
        page._fail(exc)
        return
    page.step_area.setCurrentIndex(4)


def write_output(page, path: str) -> bool:
    """Step 5's Save, minus the dialog -- `import_page.save_as` delegates
    here. I2: writes exactly what Preview already rendered into
    `page.preview_pane`, with NO rebuild of its own -- the rebuild lives
    only in `show_scene_step`, before Preview is shown. A second rebuild
    here used to mean Preview and Save could disagree: opening Tools >
    Vocabulary from the Save step and teaching a term (or a classifier.
    yaml that broke in between) changed, or blocked, what got written,
    even though the operator had already reviewed the preview and the
    Scene step's table against the OLDER vocabulary."""
    try:
        Path(path).write_text(page.preview_pane.toPlainText(), encoding="utf-8")
    except OSError as exc:
        page._fail(exc)
        return False
    return True
