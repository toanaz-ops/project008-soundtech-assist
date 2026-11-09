"""propose() and to_patches(): the deterministic automix entry points.

Pure: the same scene, document, options and knowledge give the same
proposal, which is what the golden tests rely on. No Qt, no network, no
model calls, and the scene and document are never mutated.
"""

from __future__ import annotations

from pathlib import Path

from wing_parser.automix import knowledge, select, stages_balance, stages_dynamics, stages_filter_eq, stages_fx
from wing_parser.automix.bounds import Bounds
from wing_parser.automix.interp import Ctx
from wing_parser.automix.options import STAGES, AutomixOptions, Proposal
from wing_parser.edit.journal import Patch


def propose(scene, document: dict, options: AutomixOptions, knowledge_dir: Path | None = None) -> Proposal:
    kb = knowledge.load(knowledge_dir)
    ctx = Ctx(document, options.strength, Bounds(kb.bounds))
    strips, skipped = select.select(scene, options)
    buses = select.fx_buses(document, kb.fx["model_roles"])
    on = options.stages
    changes, hints, trim = [], [], 0.0
    if "hpf" in on:
        changes += stages_filter_eq.hpf(ctx, kb, strips)
    if "eq" in on:
        changes += stages_filter_eq.eq(ctx, kb, strips, options.genre)
    if "gate" in on:
        changes += stages_dynamics.gate(ctx, kb, strips, options.genre)
    if "comp" in on:
        changes += stages_dynamics.comp(ctx, kb, strips, options.genre)
    if "fader" in on:
        found, trim = stages_balance.fader(ctx, kb, strips, options)
        changes += found
    if "fx" in on:
        found, extra = stages_fx.fx(ctx, kb, buses, options)
        changes, hints = changes + found, hints + extra
    if "sends" in on:
        changes += stages_fx.sends(ctx, kb, strips, buses, options.genre)
    if "inserts" in on:
        found, extra = stages_balance.inserts(ctx, kb, strips, options.genre)
        changes, hints = changes + found, hints + extra
    order = {stage: index for index, stage in enumerate(STAGES)}
    changes.sort(key=lambda c: (order[c.stage], _target_key(c.target), c.path))
    return Proposal(options, tuple(changes), tuple(hints), tuple(skipped + ctx.skipped),
                    trim, tuple(kb.warnings))


def _target_key(target: str) -> tuple:
    kind, _, number = target.partition(".")
    return (kind, int(number)) if number.isdigit() else (kind, 0)


def to_patches(proposal: Proposal) -> list:
    genre = proposal.options.genre
    return [Patch(c.path, c.before, c.after, f"automix:{genre}:{c.stage}", c.label)
            for c in proposal.changes]
