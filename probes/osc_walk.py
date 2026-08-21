"""Walk the WING's self-describing OSC tree and write out the schema.

Read-only by construction: it reuses osc_probe.message(), which has no
way to encode an argument, so no packet it emits can carry a value.

Numeric sibling collapse. /ch has forty children with identical shapes,
and so do the bus, aux, matrix and send families. Walking all of them
would send tens of thousands of packets to say the same thing forty
times. Instead, when every child of a node is numeric-looking, this
walks the *first* one in full and records the sibling list beside it.
The output therefore describes the schema, not one console's inventory
-- which is what a repair descriptor needs.
"""

from __future__ import annotations

import json
import re
import socket
import time

from osc_probe import CONSOLE, decode, message

NUMERIC = re.compile(r"^(MX)?[0-9]+$")
TIMEOUT = 0.35


class Walker:
    def __init__(self) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("0.0.0.0", 0))
        self.sock.settimeout(TIMEOUT)
        self.sent = 0
        self.schema: dict[str, dict] = {}

    def ask(self, address: str):
        """Send one query, return (typetags, values) or None."""
        self.sock.sendto(message(address), CONSOLE)
        self.sent += 1
        deadline = time.time() + TIMEOUT
        while time.time() < deadline:
            try:
                data, _ = self.sock.recvfrom(65535)
            except socket.timeout:
                return None
            text = decode(data)
            if text.startswith(address + " ") or text.startswith(address + "  "):
                parts = text.split("  ", 2)
                if len(parts) == 3:
                    return parts[1], json.loads(parts[2].replace("'", '"'))
                return parts[1] if len(parts) > 1 else "", []
        return None

    def is_container(self, address: str, tags: str, values: list) -> bool:
        """All-string replies are ambiguous when there is exactly one.

        A container lists child names; a leaf like /ch/1/name returns
        its single string value. Distinguished by trying to descend:
        a real child answers, a value does not.
        """
        if not values or set(tags.lstrip(",")) != {"s"}:
            return False
        if len(values) > 1:
            return True
        return self.ask(f"{address}/{values[0]}") is not None

    def walk(self, address: str = "", depth: int = 0, budget: int = 6) -> dict:
        if depth > budget:
            return {"truncated": True}

        answer = self.ask(address or "/")
        if answer is None:
            return {"no_reply": True}
        tags, values = answer

        if not self.is_container(address or "/", tags, values):
            return {"leaf": True, "tags": tags, "example": values}

        children = [str(v) for v in values]
        numeric = [c for c in children if NUMERIC.match(c)]

        node: dict = {"children": children}
        if numeric and len(numeric) == len(children):
            # Homogeneous family: describe one, list the rest.
            node["family"] = True
            node["members"] = children
            node["shape_of"] = children[0]
            node["shape"] = self.walk(f"{address}/{children[0]}", depth + 1, budget)
            return node

        node["nodes"] = {}
        for child in children:
            node["nodes"][child] = self.walk(f"{address}/{child}", depth + 1, budget)
        return node


if __name__ == "__main__":
    walker = Walker()
    started = time.time()
    # $-prefixed roots are live meters and control-surface state, not
    # scene parameters; skipped to keep the walk about what a scene has.
    tree = {}
    root = walker.ask("/")
    for branch in [c for c in root[1] if not c.startswith("$")]:
        print(f"walking /{branch} ...", flush=True)
        tree[branch] = walker.walk(f"/{branch}")

    out = "wing-osc-schema.json"
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(tree, handle, indent=1, ensure_ascii=False)
    print(f"\n{walker.sent} queries in {time.time() - started:.0f}s -> {out}")
