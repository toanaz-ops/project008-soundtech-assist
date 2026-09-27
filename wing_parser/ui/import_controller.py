"""The GUI's import brain: pure functions over the ingest pipeline.

Every decision the import wizard page needs lives here as a plain
function with no Qt import, so each one is testable headless. The
behaviour mirrors `showcontext/ingest/wizard.py` -- same failure
shapes, same vocabulary lookup, same kill-switch gates -- minus the
printing and stdin, which are the wizard's business and become the UI's.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from wing_parser.classifier.llm import kill_switch_on
from wing_parser.classifier.provider import ProviderError
from wing_parser.showcontext.ingest import build, emit, guess, mapping, propose, sheet
from wing_parser.showcontext.ingest.sample import sample_workbook
from wing_parser.showcontext.ingest.suggest import propose_mapping


def sample(xlsx):
    """Each sheet sampled as text lines, for a what-is-in-here preview."""
    return sample_workbook(xlsx)


def proposal_for(xlsx, provider_factory):
    """One mapping-assist attempt; any provider-shaped failure is None.

    ValueError joins ProviderError because load_config raises it for a
    missing or malformed named config file; OSError and
    zipfile.BadZipFile cover sampling a workbook that vanished or was
    never an xlsx. The caller shows "no model assist" and walks manual
    questions -- exactly `wizard._propose_or_none`, minus printing.
    """
    if kill_switch_on():
        return None
    try:
        return propose_mapping(xlsx, provider_factory())
    except (ProviderError, ValueError, OSError, zipfile.BadZipFile):
        return None


def read_with(xlsx, sheet_name: str | None, header_row: int,
              columns: dict, headers: dict):
    """Sheet read plus resolved columns; failures raise untouched.

    A bad sheet name, an empty header row, a letter past the sheet's
    extent or a header text that matches nothing all surface as the
    pipeline's own (OSError, ValueError, sheet.MissingExtra) so the
    page can show one error line, not invent a second taxonomy.
    """
    read = sheet.read_sheet(xlsx, sheet_name, header_row)
    raw = mapping.RawMapping(
        source=f"{Path(xlsx).stem} (gui)",
        sheet=sheet_name,
        header_row=header_row,
        columns=dict(columns),
        headers=dict(headers),
    )
    resolved = mapping.resolve_columns(raw, read.headers, read.last_column)
    return read, resolved


def build_result(read, resolved, directory=None):
    """Rows and a resolved mapping become BuiltSegments, the effective
    cuesheet vocabulary (defaults + his edits, Task 2) first.

    `Vocabulary.load(directory)` is called fresh on every call rather
    than cached: the autouse test fixture points the default directory
    at a throwaway path per test, and Settings/the Vocabulary window can
    change what a real directory holds while the app is running.
    `directory=None` resolves through `Vocabulary.load`'s own default
    (`config.knowledge_dir()`), unchanged from before this parameter
    existed; a caller that already knows which knowledge dir it is
    teaching into -- the Terms step, via `page._directory` -- passes it
    explicitly (fix round 1, controller ruling R1) so a Preview or Save
    rebuilt after a Record/Ignore reflects the SAME vocabulary the
    Terms step just wrote to, not whatever the process-wide default
    happens to be.
    """
    from wing_parser.classifier import vocabulary as vocab_module

    vocabulary = vocab_module.Vocabulary.load(directory)
    return build.build(
        read.rows, resolved, vocabulary,
        blank_rows=read.blank_rows, headers=read.headers,
    )


def preview_text(xlsx, result, scene=None) -> str:
    """The rendered YAML document, under the workbook's stem as show
    name. `scene`, given, adds the --scene cross-check proposals exactly
    as the CLI's --scene does (design spec §5) -- commented-out cues,
    never live ones."""
    proposals = propose.for_segments(result, scene) if scene is not None else None
    return emit.render(Path(xlsx).stem, result, proposals)


def unresolved(result):
    """Terms the vocabulary could not read, deduplicated, first-seen order."""
    return guess.unresolved_terms(result)


def context_for(terms, rows) -> dict[str, list[str]]:
    """Up to two rendered rows per term, as context for the guess.

    Ported verbatim from `wizard._context_for`: importing the private
    would couple the UI package to the CLI wizard's internals, and the
    two must be free to drift in presentation, never in this shape.
    """
    context: dict[str, list[str]] = {}
    for term in terms:
        hits: list[str] = []
        for row in rows:
            cells = "; ".join(
                f"{letter}: {value}"
                for letter, value in sorted(row.cells.items())
                if value.strip()
            )
            line = f"row {row.number}: {cells}"
            if term.casefold() in line.casefold():
                hits.append(line)
                if len(hits) == 2:
                    break
        context[term] = hits
    return context
