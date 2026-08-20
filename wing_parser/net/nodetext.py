"""Parse the node-text body of a `,s *` reply (design doc S2.7 / S3).

**Cross-check only -- never on the snapshot path (design doc S4).** S2.3
measured that node-dump values are lossy display text, not the native value:
`ch.1.flt.hcf` reads back `10018.26074` from a `.snap` file and a per-leaf
GET, but only `10k02` from a `,s *` node dump; `ch.1.eq.lq` is
`0.997970223` per-leaf and `1.00` in the dump. This module therefore returns
the RAW TOKEN STRINGS the console sent -- for shape inspection (which keys
exist, how they nest) and human cross-checking only. It never parses a
float, decodes `k`-notation, or maps `-oo` to a sentinel: any of those would
dress up a lossy display string as if it were the exact value, which it is
not. A caller that wants a value reads the leaf directly (`net/client.py` +
`codec.leaf_value`) and never takes one from here.

Grammar (design doc S3), inferred entirely from captured replies in
tests/data/wing_osc_fixtures.json -- nothing here is invented beyond what
those replies and S2.7's quoting example show:

  * the body is a comma-separated list of tokens, read left to right
  * a token is `key=value`, where `key` may itself contain `.` to descend
    into (and create, for parsing purposes) a child node one level per dot
    -- `set.srcauto=0` assigns into `set`, descending from wherever the
    previous token left off
  * a token with *no* embedded `.` assigns into whatever node the *previous*
    token's descent left the cursor in (`altsrc=0` right after
    `set.srcauto=0` stays inside `set`)
  * one or more LEADING dots on a token pop that many levels back up
    *before* any descent in the same token is applied -- `.conn.grp=LCL`
    pops one level then descends into `conn`; `..dir.on=0` pops two levels
    then descends into `dir`
  * a token that is nothing but leading dots (most bodies end with a bare
    `.`) pops and assigns nothing -- it must not create a phantom key
  * a value may be wrapped in single quotes; this is how the console escapes
    a value that itself contains `,` or `=`, e.g. `name='A,B=C'` (S2.7). A
    quoted value's `,`/`=` are literal and must not be treated as grammar.

No fixture exercises a quoted value containing an escaped or doubled single
quote. This parser does not invent handling for that case -- an embedded
`'` inside a quoted value will be read as the closing quote, which is a
known gap, not a silent guess.
"""

from __future__ import annotations

from typing import Any


class NodeTextError(ValueError):
    """A `,s *` body did not parse as the S3 dot/comma/quote grammar."""


def parse_node_text(text: str) -> dict[str, Any]:
    """Parse one node-text body into a nested dict of raw string tokens.

    Every leaf value in the result is the console's literal text for that
    field -- see the module docstring for why nothing here converts it.
    """
    tree: dict[str, Any] = {}
    stack: list[dict[str, Any]] = [tree]  # stack[0] is always the root node

    tokens = _split_top_level(text)
    last_index = len(tokens) - 1
    for index, token in enumerate(tokens):
        if token == "":
            if index != last_index:
                raise NodeTextError(f"empty assignment inside node text: {text!r}")
            continue  # a trailing comma, not a phantom key

        stripped = token.lstrip(".")
        pop_count = len(token) - len(stripped)
        if pop_count:
            if pop_count >= len(stack):
                raise NodeTextError(
                    f"{token!r} pops {pop_count} level(s) past the root: {text!r}"
                )
            del stack[len(stack) - pop_count :]

        if stripped == "":
            continue  # bare dots: pop only, nothing to assign (S3)

        if "=" not in stripped:
            raise NodeTextError(f"assignment has no '=': {token!r} in {text!r}")
        keypath, raw_value = stripped.split("=", 1)
        segments = keypath.split(".")
        if not keypath or any(segment == "" for segment in segments):
            raise NodeTextError(f"malformed key path: {token!r} in {text!r}")

        node = stack[-1]
        for segment in segments[:-1]:
            child = node.setdefault(segment, {})
            if not isinstance(child, dict):
                raise NodeTextError(
                    f"{segment!r} is already a leaf, cannot descend: {token!r} in {text!r}"
                )
            node = child
            stack.append(node)

        node[segments[-1]] = _unquote(raw_value, token, text)

    return tree


def _split_top_level(text: str) -> list[str]:
    """Split on commas that are not inside a single-quoted value.

    A quoted value's own commas (S2.7's `name='A,B=C'`) must survive intact
    for the caller to split on `=` afterwards.
    """
    tokens: list[str] = []
    current: list[str] = []
    in_quote = False
    for char in text:
        if char == "'":
            in_quote = not in_quote
            current.append(char)
        elif char == "," and not in_quote:
            tokens.append("".join(current))
            current = []
        else:
            current.append(char)
    if in_quote:
        raise NodeTextError(f"unterminated quote in node text: {text!r}")
    tokens.append("".join(current))
    return tokens


def _unquote(raw_value: str, token: str, text: str) -> str:
    """Strip one layer of single quotes; the content inside is never rewritten."""
    if not raw_value.startswith("'"):
        return raw_value
    if len(raw_value) < 2 or not raw_value.endswith("'"):
        raise NodeTextError(f"unterminated quoted value: {token!r} in {text!r}")
    return raw_value[1:-1]
