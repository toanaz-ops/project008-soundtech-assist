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

from wing_parser.classifier import cache
from wing_parser.classifier.llm import kill_switch_on
from wing_parser.classifier.normalize import clean
from wing_parser.classifier.provider import ProviderError
from wing_parser.showcontext.ingest import build, emit, guess, mapping, sheet
from wing_parser.showcontext.ingest.suggest import propose_mapping


def sample(xlsx):
    """Each sheet sampled as text lines, for a what-is-in-here preview."""
    from wing_parser.showcontext.ingest.sample import sample_workbook

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


def build_result(read, resolved):
    """Rows and a resolved mapping become BuiltSegments, vocabulary first.

    The cuesheet vocabulary is whatever `classifier.yaml` holds right
    now (the autouse test fixture keeps that file off the real disk);
    unresolved fragments stay comments, never guesses.
    """
    vocabulary = cache.load()["cuesheet"]
    return build.build(
        read.rows,
        resolved,
        lambda term: vocabulary.get(clean(term)),
        blank_rows=read.blank_rows,
        headers=read.headers,
    )


def preview_text(xlsx, result) -> str:
    """The rendered YAML document, under the workbook's stem as show name."""
    return emit.render(Path(xlsx).stem, result, None)


def unresolved(result):
    """Terms the vocabulary could not read, deduplicated, first-seen order."""
    return guess.unresolved_terms(result)


def guesses_for(terms, context_by_term, provider_factory):
    """One model guess per term; per-term errors collapse to None entries.

    The list of (term, Classification | None) pairs is the whole result:
    the UI decides how to present a dead provider per term instead of
    losing every other term to one failure. With WING_DISABLE_LLM set,
    no provider is ever constructed and the answer is simply [].
    """
    if kill_switch_on():
        return []
    results = []
    for term in terms:
        try:
            found = guess.propose_term(
                term, context_by_term.get(term, []), provider_factory()
            )
        except Exception:  # noqa: BLE001 - degrade like every model path
            found = None
        results.append((term, found))
    return results


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


def record_term(term, classification, directory=None) -> None:
    """Write through the same atomic cache path every classification takes."""
    cache.remember(term, "cuesheet", classification, directory=directory)
