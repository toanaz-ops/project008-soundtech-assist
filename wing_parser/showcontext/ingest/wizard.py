"""Interactive import: the model proposes, ToanAZ presses Enter or edits.

Every question shows a default from the proposal and accepts bare Enter.
A provider failure prints one line and falls back to asking the same
questions with no defaults -- the manual G2a flow with better manners,
never a traceback.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

from wing_parser.classifier.normalize import clean
from wing_parser.showcontext.ingest import build, emit, guess, mapping, propose, sheet


def _ask(prompt: str, default: str, input_fn) -> str:
    suffix = f" [{default}]" if default else ""
    answer = input_fn(f"{prompt}{suffix}: ").strip()
    return answer or default


def _propose_or_none(xlsx, print_fn, knowledge_dir=None):
    """One assist attempt; any provider-shaped failure is one line.

    ValueError joins ProviderError because resolve_config raises it for
    a named config file that is pinned but missing or malformed -- the
    same hand-edited-file situation the rest of this CLI turns into an
    error line, and exactly what the one-line contract promises. OSError and
    zipfile.BadZipFile cover sampling a workbook that vanished or is not
    an xlsx at all, which happens before the provider is ever called.
    """
    import zipfile

    from wing_parser.classifier.llm import kill_switch_on
    from wing_parser.classifier.provider import (
        ProviderError,
        make_provider,
        resolve_config,
    )
    from wing_parser.showcontext.ingest.suggest import propose_mapping

    if kill_switch_on():
        print_fn(
            "(model assist disabled: WING_DISABLE_LLM is set "
            "-- continuing manually)"
        )
        return None

    try:
        provider = make_provider(resolve_config(knowledge_dir))
        return propose_mapping(xlsx, provider)
    except (ProviderError, ValueError, OSError, zipfile.BadZipFile) as exc:
        print_fn(f"(no model assist: {exc} -- continuing manually)")
        return None


def run_wizard(xlsx, *, input_fn=input, print_fn=print, output=None,
               force=False, scene=None, one_shot=False, knowledge_dir=None):
    source = Path(xlsx)
    if not source.exists():
        print_fn(f"error: {source} does not exist.")
        return 1

    destination = Path(output) if output else None
    if destination is not None and destination.exists() and not force:
        print_fn(
            f"error: {destination} already exists. Pass --force to replace it."
        )
        return 1

    proposal = _propose_or_none(xlsx, print_fn, knowledge_dir)
    if proposal is not None and proposal.problems:
        # Spec section 4: a proposal the checker could not verify is shown
        # marked, BEFORE its values become any question's default.
        print_fn(
            "(proposal unverified: " + "; ".join(proposal.problems)
            + "; check every default)"
        )
    try:
        sheet_name = _ask("Sheet", proposal.sheet if proposal else "", input_fn)
        header_row = int(_ask(
            "Header row", str(proposal.header_row) if proposal else "1", input_fn
        ))
        read = sheet.read_sheet(xlsx, sheet_name or None, header_row)
        print_fn("Columns: " + ", ".join(
            f"{k}={v}" for k, v in sorted(read.headers.items())
        ))
        core = {}
        for field in ("id", "time", "title"):
            default = proposal.columns.get(field, "") if proposal else ""
            answer = _ask(f"Column letter for {field}", default, input_fn)
            if answer:
                core[field] = answer.upper()
        heads = {}
        for field in ("performers", "note", "sound", "lighting", "led"):
            default = proposal.headers.get(field, "") if proposal else ""
            answer = _ask(f"Header text for {field}", default, input_fn)
            if answer:
                heads[field] = answer
        raw = mapping.RawMapping(
            source=f"{Path(xlsx).stem} (wizard)", sheet=sheet_name or None,
            header_row=header_row, columns=core, headers=heads,
        )
        # Resolved before anything is saved: a mapping that cannot be
        # consumed must never reach disk looking finished.
        resolved = mapping.resolve_columns(raw, read.headers, read.last_column)
    # StopIteration rides along: a real stdin at EOF raises EOFError, but
    # an exhausted answer iterator (how tests script the wizard) raises
    # StopIteration through input_fn -- both mean "nobody is answering".
    except (EOFError, StopIteration):
        print_fn("input closed -- mapping not saved")
        return 1
    except (OSError, ValueError, sheet.MissingExtra) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    map_doc = {
        "source": raw.source,
        "sheet": raw.sheet,
        "header_row": header_row,
        "columns": core,
        "headers": heads,
    }
    map_path = Path(f"{Path(xlsx).stem}.map.yaml")
    map_path.write_text(_dump_yaml(map_doc), encoding="utf-8")
    print_fn(f"mapping saved: {map_path}")
    if one_shot:
        return 0
    try:
        return _finish(
            xlsx, read, resolved,
            output=output, force=force, scene=scene, print_fn=print_fn,
            input_fn=input_fn, knowledge_dir=knowledge_dir,
        )
    except (EOFError, StopIteration):
        print_fn("input closed -- import stopped")
        return 1


def _dump_yaml(doc: dict) -> str:
    from ruamel.yaml import YAML

    engine = YAML()
    stream = io.StringIO()
    engine.dump(doc, stream)
    return stream.getvalue()


def _context_for(terms, rows) -> dict[str, list[str]]:
    """Up to two rendered rows per term, as context for the guess."""
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


def _finish(xlsx, read, resolved, *, output, force, scene, print_fn,
            input_fn=input, knowledge_dir=None):
    # Mirrors commands.showcontext_import from vocabulary onward; kept here
    # so the wizard owns one flow instead of shelling back through argparse.
    from wing_parser.classifier import cache

    try:
        vocabulary = cache.load().get("cuesheet", {})
        result = build.build(
            read.rows,
            resolved,
            lambda term: vocabulary.get(clean(term)),
            blank_rows=read.blank_rows,
            headers=read.headers,
        )
    except (OSError, ValueError, sheet.MissingExtra) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    proposals = None
    if scene is not None:
        from wing_parser import WingScene

        try:
            loaded = WingScene.load(scene)
        except (OSError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        proposals = propose.for_segments(result, loaded)

    text = emit.render(Path(xlsx).stem, result, proposals)
    destination = Path(output) if output else None
    if destination is None:
        print_fn(text)
    else:
        destination.write_text(text, encoding="utf-8")

    terms = guess.unresolved_terms(result)
    if terms:
        from wing_parser.classifier.llm import kill_switch_on

        if kill_switch_on():
            print_fn(
                "(model assist disabled: WING_DISABLE_LLM is set "
                "-- unresolved terms stay as comments)"
            )
            return 0
        from wing_parser.classifier.provider import make_provider, resolve_config

        guess.offer_terms(
            terms, _context_for(terms, read.rows),
            provider_factory=lambda: make_provider(resolve_config(knowledge_dir)),
            input_fn=input_fn, print_fn=print_fn,
        )
    return 0
