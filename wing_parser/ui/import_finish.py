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
    cross-check proposals if any -- Skip passes scene=None, and the file
    is byte-for-byte what today's (pre-wave-4) Save produces. `scene` is
    already `page.scene_step.chosen_scene` by the time this runs -- the
    step sets it before emitting -- so write_output can read it back
    from there and render the SAME thing Save later writes."""
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
    here. Refreshed first, same as Preview; a failed refresh must not be
    followed by writing the stale mapping-time result (fix round 2). The
    chosen scene threads through exactly as it did into Preview, so the
    saved file is always byte-identical to what was just previewed."""
    if not refresh_result(page):
        return False
    try:
        Path(path).write_text(
            ic.preview_text(
                page._xlsx, page._result, scene=page.scene_step.chosen_scene),
            encoding="utf-8",
        )
    except (OSError, ValueError) as exc:
        page._fail(exc)
        return False
    return True
