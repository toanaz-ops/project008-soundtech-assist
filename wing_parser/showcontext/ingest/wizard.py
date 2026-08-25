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
from wing_parser.showcontext.ingest import build, emit, mapping, propose, sheet


def _ask(prompt: str, default: str, input_fn) -> str:
    suffix = f" [{default}]" if default else ""
    answer = input_fn(f"{prompt}{suffix}: ").strip()
    return answer or default


def _propose_or_none(xlsx, print_fn):
    """One assist attempt; any provider-shaped failure is one line.

    ValueError joins ProviderError here because load_config raises it for
    a named config file that is missing or malformed -- the same
    hand-edited-file situation the rest of this CLI turns into an error
    line, and exactly what the one-line contract promises.
    """
    from wing_parser.classifier.provider import (
        ProviderError,
        load_config,
        make_provider,
    )
    from wing_parser.showcontext.ingest.suggest import propose_mapping

    try:
        provider = make_provider(load_config(None))
        return propose_mapping(xlsx, provider)
    except (ProviderError, ValueError) as exc:
        print_fn(f"(no model assist: {exc} -- continuing manually)")
        return None


def run_wizard(xlsx, *, input_fn=input, print_fn=print, output=None,
               force=False, scene=None, one_shot=False):
    destination = Path(output) if output else None
    if destination is not None and destination.exists() and not force:
        print_fn(
            f"error: {destination} already exists. Pass --force to replace it."
        )
        return 1

    proposal = _propose_or_none(xlsx, print_fn)
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
    return _finish(
        xlsx, read, resolved,
        output=output, force=force, scene=scene, print_fn=print_fn,
    )


def _dump_yaml(doc: dict) -> str:
    from ruamel.yaml import YAML

    engine = YAML()
    stream = io.StringIO()
    engine.dump(doc, stream)
    return stream.getvalue()


def _finish(xlsx, read, resolved, *, output, force, scene, print_fn):
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
    return 0
