"""Spec S8: the write path must be structurally unreachable from wing_parser/ui/.

Not a promise, a scan (S8.2). Two rules, each an `ast` walk over every
`.py` under `wing_parser/ui/`:

1. No import, static or dynamic, reaches `wing_parser.net.write` -- plain
   `import`/`from ... import` shapes, plus `importlib.import_module(...)`,
   `import_module(...)`, `__import__(...)` with a literal first argument
   naming it (or `wing_parser.net` with `write` in a `fromlist`, or the
   relative `".write"` against a literal `package`, which D-44 taught it
   to resolve). A computed name is a blind spot either way.
2. No write verb (`set`/`toggle`/`node_write`/`push`) is REACHED through
   `wing_parser.net`. The import table binds anything under `wing_parser`
   -- the top package and `wing_parser.net` included -- and `_net_target`
   rebuilds the dotted path an `Attribute` chain spells before deciding, so
   `from wing_parser import net` then `net.write.push(...)`, and a bare
   `import wing_parser` then `wing_parser.net.write.push(...)`, are both
   offences while `wing_parser.config.set(...)` is not. Not bare-name
   matching either: `self.cancel.set()` (`live_watch_session.py:143`) and
   `self._cancelled.set()` (`workers.py:69`), both `threading.Event`, end
   at `self`, unbound.

`Transport.client(host)` (used at `live_watch_session.py:87`) returns a
bare `WingClient`; rule 2 need not name it, since the four verbs are
module *functions* in `net/write.py`, not `WingClient` methods -- the
only real write through this seam, `write.node_write(client, ...)`,
needs an import that rule 1 already catches. Pinned by
`test_write_verbs_are_not_client_methods`, not just assumed.

Wave 3 (W4, design §8.4) turns this into an **allow-list of one**:
`wing_parser/ui/live_write.py` is the single door to the write path.
The allow-list is the path RELATIVE TO THE SCAN ROOT, matched against
`ALLOWED_WRITE_MODULES`: never `path.name`, which would hand the same
rights to any `ui/<sub>/live_write.py`, and never a substring or suffix of
the offender line -- `bus_live_write.py` ends with the allow-listed name
and must still be reported.

Rule 1 is **narrowed** there, not waived: an allow-listed file may bind
the write MODULE (`import wing_parser.net.write`, `from wing_parser.net
import write`), whose verbs are then attribute access that rule 2 sees,
or take `ALLOWED_WRITE_IMPORTS` off it by name. `from
wing_parser.net.write import push` stays an offence, because a bare
`push(host, ...)` contains no attribute access for rule 2 to find.
Rule 2 therefore also tracks names bound to a verb that way, and
`toggle`, `node_write` and `push` stay offences in every file, that one
included -- which `test_the_allow_listed_module_names_set_and_nothing_else`
pins with a scan wider than rule 2's: an attribute REFERENCE, not only
a call, because `live_write.py` hands `write.set` to a dataclass field.

Blind spot shared with `test_ui_texts.py`: a local variable assigned from
a net-bound call (`wc = client.WingClient(host)` then `wc.set(...)`) is
invisible to rule 2 -- only names bound directly by an `Import`/`ImportFrom`
are tracked; `client.WingClient(host).set(...)` in one expression IS caught.

Second blind spot, by construction: a verb reached WITHOUT naming it,
`getattr(write, "push")(host, ...)`. Both scans read `ast.Attribute` and
`ast.Name`, and `"push"` there is a string constant, so neither sees it.
Rule 1 still catches the import that binds `write` in any file but the
allow-listed one, which is the lock that matters; inside `live_write.py`
it would pass. Closing it means matching `getattr` with a literal second
argument, which is a scan change, not a fix to make in passing.
"""
from __future__ import annotations

import ast
from importlib.util import resolve_name
from pathlib import Path

import wing_parser.ui as ui_package

UI_ROOT = Path(ui_package.__file__).resolve().parent

WRITE_VERBS = {"set", "toggle", "node_write", "push"}

_NET = "wing_parser.net"

#: W4/§8.4: exactly one `ui/` module may reach `wing_parser.net.write`, and
#: it exists in order to call ONE verb there. Matched on the path RELATIVE
#: TO THE SCAN ROOT -- never `path.name`, which hands the same rights to
#: any `ui/<sub>/live_write.py` somebody adds, and never
#: `name in offender_line`, which would exempt `bus_live_write.py` too --
#: so the scan behaves identically in `UI_ROOT` and in a `tmp_path`.
#: Adding a second entry re-opens the blast radius this file exists to
#: bound -- that is a spec change, not a fix.
ALLOWED_WRITE_MODULES = frozenset({Path("live_write.py")})


def _is_allowed(path: Path, root: Path) -> bool:
    return path.relative_to(root) in ALLOWED_WRITE_MODULES

#: The one verb the allow-listed module may use. `toggle` sends `,i -1` and
#: flips whatever the desk holds NOW (`write.py:139-142`), so its outcome
#: is not the `after` the countdown showed; `node_write` and `push` both
#: break F1's one-leaf-per-transmission at the transport. Offences
#: everywhere, that module included.
ALLOWED_VERB = "set"

#: What the allow-listed file may take off `wing_parser.net.write` BY NAME.
#: The verb, plus the result and error types it must name to hand
#: `write.py`'s own verdict back to its caller instead of re-deriving it.
#: Anything else -- above all another verb -- is an offence there too: a
#: bare `push(host, ...)` is a write with no attribute access anywhere in
#: the file, which is exactly the shape a waived rule 1 would hide.
ALLOWED_WRITE_IMPORTS = frozenset({ALLOWED_VERB, "SetResult", "SerialMismatchError"})


def _py_files(root: Path):
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" not in path.parts:
            yield path


def _net_bound_names(tree: ast.Module) -> dict[str, str]:
    """Local name -> the dotted module it names, for anything under
    `wing_parser` (Import/ImportFrom only).

    `wing_parser` and `wing_parser.net` are bound too, not just things
    under `wing_parser.net`: `from wing_parser import net` binds `net` off
    the PACKAGE, and `import wing_parser` binds only the top name, so a
    table keyed on "the import path starts with wing_parser.net" held
    nothing for either and `net.write.push(...)` walked straight past both
    rules. `_net_target` decides what is actually a net reach.
    """
    bound: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name == "wing_parser" or a.name.startswith("wing_parser."):
                    # `import a.b` binds the TOP package unless aliased.
                    bound[a.asname or a.name.split(".")[0]] = (
                        a.name if a.asname else a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "wing_parser" or module.startswith("wing_parser."):
                for a in node.names:
                    bound[a.asname or a.name] = f"{module}.{a.name}"
    return bound


def _import_reaches_write(node: ast.stmt) -> bool:
    if isinstance(node, ast.Import):
        return any(
            a.name == "wing_parser.net.write" or a.name.startswith("wing_parser.net.write.")
            for a in node.names
        )
    if isinstance(node, ast.ImportFrom):
        module = node.module or ""
        if module == "wing_parser.net.write" or module.startswith("wing_parser.net.write."):
            return True
        return module == "wing_parser.net" and any(a.name == "write" for a in node.names)
    return False


def _dynamic_call_reaches_write(node: ast.Call) -> str | None:
    """Callee name for a dynamic import reaching write, else None (literal args only)."""
    func = node.func
    if isinstance(func, ast.Name) and func.id in {"import_module", "__import__"}:
        name = func.id
    elif isinstance(func, ast.Attribute) and func.attr == "import_module":
        name = "import_module"
    else:
        return None
    args = node.args
    if not args or not isinstance(args[0], ast.Constant) or not isinstance(args[0].value, str):
        return None
    target = args[0].value
    if target.startswith("."):      # D-44: relative, resolved like import_module does
        pkg = args[1] if len(args) > 1 else next(
            (kw.value for kw in node.keywords if kw.arg == "package"), None)
        if not isinstance(pkg, ast.Constant) or not isinstance(pkg.value, str):
            return None
        try:
            target = resolve_name(target, pkg.value)
        except ImportError:         # more leading dots than the package has parts
            return None
    if target == "wing_parser.net.write" or target.startswith("wing_parser.net.write."):
        return name
    if target != "wing_parser.net":
        return None
    fromlist = args[3] if len(args) >= 4 else next(
        (kw.value for kw in node.keywords if kw.arg == "fromlist"), None
    )
    ok = isinstance(fromlist, (ast.List, ast.Tuple)) and any(
        isinstance(e, ast.Constant) and e.value == "write" for e in fromlist.elts
    )
    return name if ok else None


def _allowed_write_import(node: ast.stmt) -> bool:
    """True only for the narrow shapes the allow-listed file may use.

    Binding the write MODULE is fine -- every verb on it is then an
    attribute access, which rule 2 reads. Binding a NAME off it is fine
    only for `ALLOWED_WRITE_IMPORTS`. A dynamic import is never allowed,
    here or anywhere: this function is not consulted for one.
    """
    if isinstance(node, ast.Import):
        return all(
            a.name == "wing_parser.net.write"
            for a in node.names
            if a.name.startswith("wing_parser.net.write")
        )
    if isinstance(node, ast.ImportFrom):
        module = node.module or ""
        if module == "wing_parser.net":
            return True         # `from wing_parser.net import write` -- the module
        if module == "wing_parser.net.write":
            return all(a.name in ALLOWED_WRITE_IMPORTS for a in node.names)
    return False


def find_write_imports(root: Path, *, skip_allowed: bool = False) -> list[str]:
    """Rule 1: every static or dynamic import reaching `wing_parser.net.write`.

    `skip_allowed` does not skip the allow-listed file, it NARROWS the
    rule there to `_allowed_write_import` -- see this module's docstring
    for why waiving it wholesale would hide a bare-name verb call.
    """
    offenders = []
    for path in _py_files(root):
        narrowed = skip_allowed and _is_allowed(path, root)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)) and _import_reaches_write(node):
                if narrowed:
                    if not _allowed_write_import(node):
                        offenders.append(
                            f"{path}:{node.lineno}: imports a name off the write path "
                            f"outside {sorted(ALLOWED_WRITE_IMPORTS)}"
                        )
                    continue
                offenders.append(f"{path}:{node.lineno}: imports the write path (wing_parser.net.write)")
            elif isinstance(node, ast.Call):
                name = _dynamic_call_reaches_write(node)
                if name:
                    offenders.append(f"{path}:{node.lineno}: {name}(...) reaches the write path (wing_parser.net.write)")
    return sorted(offenders)


def _net_target(node, bound: dict[str, str]) -> str | None:
    """The `wing_parser.net...` module a verb is reached THROUGH, else None.

    Walks an Attribute/Call chain down to its leftmost `Name` and rebuilds
    the dotted path the attributes spell, resolving the leftmost name
    through `bound`: `net.write` under `from wing_parser import net`, and
    `wing_parser.net.write` under a bare `import wing_parser`, both land on
    `wing_parser.net.write`. `wing_parser.config.set(...)` lands on
    `wing_parser.config` and is no offence -- a scan that cried wolf there
    would be turned off.

    A `Call` in the chain (`client.WingClient(host).set(...)`) breaks the
    dotted rebuild but NOT the match: the leftmost binding alone decides,
    which is what this function did before it could resolve chains.
    """
    parts: list[str] = []
    through_call = False
    while node is not None:
        if isinstance(node, ast.Name):
            if node.id not in bound:
                return None
            dotted = bound[node.id] if through_call else ".".join(
                [bound[node.id], *reversed(parts)])
            return dotted if dotted == _NET or dotted.startswith(_NET + ".") else None
        if isinstance(node, ast.Attribute):
            parts.append(node.attr)
            node = node.value
        elif isinstance(node, ast.Call):
            through_call = True
            node = node.func
        else:
            return None
    return None


def _verb_bound_names(tree: ast.Module) -> dict[str, str]:
    """Local names bound to a write VERB by `from wing_parser.net.write
    import <verb>`.

    Without this table a bare `push(host, {})` is invisible to both verb
    scans, which read `ast.Attribute`. Rule 1 catches the import itself
    everywhere -- including, now, inside the allow-listed file -- but a
    second lock on the call site costs four lines.
    """
    bound: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or (node.module or "") != "wing_parser.net.write":
            continue
        for a in node.names:
            if a.name in WRITE_VERBS:
                bound[a.asname or a.name] = f"wing_parser.net.write.{a.name}"
    return bound


def find_write_verb_calls(root: Path, *, skip_allowed: bool = False) -> list[str]:
    """Rule 2: a write-verb call on a `wing_parser.net` binding, or on a
    bare name imported from the write module.

    `skip_allowed` leaves the allow-listed file out entirely -- it is
    checked instead, and more strictly, by `find_write_verb_uses` against
    `ALLOWED_VERB`.
    """
    offenders = []
    for path in _py_files(root):
        if skip_allowed and _is_allowed(path, root):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        net_bound = _net_bound_names(tree)
        verb_bound = _verb_bound_names(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr in WRITE_VERBS:
                target = _net_target(func.value, net_bound)
                if target:
                    offenders.append(
                        f"{path}:{node.lineno}: calls .{func.attr}(...) on {target!r}"
                    )
            elif isinstance(func, ast.Name) and func.id in verb_bound:
                offenders.append(
                    f"{path}:{node.lineno}: calls .{verb_bound[func.id].rsplit('.', 1)[1]}(...) "
                    f"as bare {func.id!r} (bound from {verb_bound[func.id]})"
                )
    return sorted(offenders)


def find_write_verb_uses(root: Path) -> list[str]:
    """Every REFERENCE to a write verb, attribute or bare name.

    Wider than `find_write_verb_calls` on purpose: `live_write.py` hands
    `write.set` to a frozen dataclass field rather than calling it inline,
    and a reference is exactly as reachable as a call. Walks every file it
    is handed, the allow-listed one included -- the allow-list is about
    WHICH verb (`ALLOWED_VERB`), not about being scanned.
    """
    offenders = []
    for path in _py_files(root):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        net_bound = _net_bound_names(tree)
        verb_bound = _verb_bound_names(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in WRITE_VERBS:
                target = _net_target(node.value, net_bound)
                if target:
                    offenders.append(
                        f"{path}:{node.lineno}: names .{node.attr} on {target!r}"
                    )
            elif isinstance(node, ast.Name) and node.id in verb_bound:
                offenders.append(
                    f"{path}:{node.lineno}: names .{verb_bound[node.id].rsplit('.', 1)[1]} "
                    f"as bare {node.id!r} (bound from {verb_bound[node.id]})"
                )
    return sorted(offenders)


def test_only_the_allow_listed_module_imports_the_write_path():
    offenders = find_write_imports(UI_ROOT, skip_allowed=True)
    assert offenders == [], (
        "the write path must not be importable from ui/ outside "
        f"{sorted(ALLOWED_WRITE_MODULES)}:\n  " + "\n  ".join(offenders)
    )


def test_no_other_ui_module_calls_a_write_verb_on_a_net_binding():
    offenders = find_write_verb_calls(UI_ROOT, skip_allowed=True)
    assert offenders == [], "no write verb may be called on a net-bound name:\n  " + "\n  ".join(offenders)


def test_the_allow_listed_module_names_set_and_nothing_else():
    """Assertion 1 of §8.4, and the reason the allow-list is not a hole."""
    used = find_write_verb_uses(UI_ROOT)
    verbs = {o.rsplit(": names .", 1)[1].split(" ")[0] for o in used}
    assert verbs <= {ALLOWED_VERB}, (
        f"only .{ALLOWED_VERB} may be named on a net binding anywhere under ui/:\n  "
        + "\n  ".join(used)
    )
    assert any("live_write.py" in o for o in used), (
        "live_write.py exists in order to name write.set -- this assertion "
        "has gone vacuous"
    )


def test_the_scan_still_catches_a_planted_push_in_an_allow_listed_name(tmp_path):
    planted = tmp_path / "live_write.py"
    planted.write_text(
        "from wing_parser.net import write\n\ndef go(host, leaves):\n"
        "    return write.push(host, leaves, confirm=True)\n",
        encoding="utf-8",
    )
    offenders = find_write_verb_uses(tmp_path)
    assert len(offenders) == 1 and ":4:" in offenders[0] and "push" in offenders[0]


def test_a_look_alike_module_name_is_not_allow_listed(tmp_path):
    """`bus_live_write.py` ENDS with the allow-listed name.

    The allow-list is `path.name` equality, not a substring or a suffix:
    a filter spelled `"live_write.py" in offender` exempts every module
    whose name merely ends that way, and the one door becomes a family
    of them. Both rules are checked, because both do their own skipping.
    """
    ui = tmp_path / "ui"
    ui.mkdir()
    (ui / "bus_live_write.py").write_text(
        "from wing_parser.net import write\n\ndef go(host):\n"
        "    return write.set(host, '/bus/1/fdr', -6.0, confirm=True)\n",
        encoding="utf-8",
    )
    imports = find_write_imports(tmp_path, skip_allowed=True)
    assert len(imports) == 1 and "bus_live_write.py" in imports[0], imports
    calls = find_write_verb_calls(tmp_path, skip_allowed=True)
    assert len(calls) == 1 and "bus_live_write.py" in calls[0], calls


def test_the_allow_listed_file_may_not_import_a_verb_by_bare_name(tmp_path):
    """Rule 1 is NOT waived wholesale for the allow-listed file.

    `from wing_parser.net.write import push` then `push(host, ...)` is a
    write with no attribute access anywhere in the file, so a waived
    rule 1 plus a verb scan that only reads `ast.Attribute` would see
    nothing at all. The import is an offence, and so is the bare call.
    """
    planted = tmp_path / "live_write.py"
    planted.write_text(
        "from wing_parser.net.write import push\n\ndef go(host):\n"
        "    return push(host, {}, confirm=True)\n",
        encoding="utf-8",
    )
    imports = find_write_imports(tmp_path, skip_allowed=True)
    assert len(imports) == 1 and ":1:" in imports[0], imports
    uses = find_write_verb_uses(tmp_path)
    assert len(uses) == 1 and ":4:" in uses[0] and "push" in uses[0], uses
    calls = find_write_verb_calls(tmp_path)
    assert len(calls) == 1 and ":4:" in calls[0] and "push" in calls[0], calls


def test_the_allow_listed_file_may_not_import_toggle_at_all(tmp_path):
    """Importing the name is the offence -- it need not be called yet."""
    planted = tmp_path / "live_write.py"
    planted.write_text(
        "from wing_parser.net.write import SetResult, toggle\n",
        encoding="utf-8",
    )
    offenders = find_write_imports(tmp_path, skip_allowed=True)
    assert len(offenders) == 1 and ":1:" in offenders[0], offenders


def test_the_allow_listed_file_may_still_use_its_three_import_shapes(tmp_path):
    """The other half: the allow-list must still ALLOW what it is for.

    `SetResult` and `SerialMismatchError` are types, not verbs -- naming
    them is how `live_write` hands `write.py`'s own verdict back to a
    caller without re-implementing it.
    """
    planted = tmp_path / "live_write.py"
    planted.write_text(
        "import wing_parser.net.write as write\n"
        "from wing_parser.net import jsontypes, write as _w\n"
        "from wing_parser.net.write import SetResult, SerialMismatchError, set\n",
        encoding="utf-8",
    )
    assert find_write_imports(tmp_path, skip_allowed=True) == []


def test_write_verbs_are_not_client_methods():
    """The Transport.client(host) seam is safe because of this; pinned."""
    from wing_parser.net.client import WingClient
    assert not any(hasattr(WingClient, verb) for verb in WRITE_VERBS)


def test_the_scan_catches_a_planted_import(tmp_path):
    planted = tmp_path / "planted_write_import.py"
    planted.write_text(
        "from wing_parser.net import write\n\ndef handler():\n    return write\n",
        encoding="utf-8",
    )
    offenders = find_write_imports(tmp_path)
    assert len(offenders) == 1
    assert str(planted) in offenders[0]
    assert ":1:" in offenders[0]


def test_the_scan_catches_a_planted_dynamic_import(tmp_path):
    planted = tmp_path / "planted_dynamic_import.py"
    planted.write_text(
        "import importlib\nimportlib.import_module('wing_parser.net.write')\n"
        "__import__('wing_parser.net', fromlist=['write'])\n",
        encoding="utf-8",
    )
    offenders = find_write_imports(tmp_path)
    assert len(offenders) == 2
    assert any(":2:" in o for o in offenders)
    assert any(":3:" in o for o in offenders)


def test_the_scan_catches_a_planted_relative_dynamic_import(tmp_path):
    """D-44: `.write` against a package is the same module, spelled shorter."""
    planted = tmp_path / "planted_relative_import.py"
    planted.write_text(
        "import importlib\nimportlib.import_module('.write', 'wing_parser.net')\n"
        "importlib.import_module('.write', package='wing_parser.net')\n",
        encoding="utf-8",
    )
    offenders = find_write_imports(tmp_path)
    assert len(offenders) == 2, offenders
    assert any(":2:" in o for o in offenders), offenders
    assert any(":3:" in o for o in offenders), offenders


def test_the_scan_ignores_an_unrelated_dot_set_call(tmp_path):
    planted = tmp_path / "unrelated_dot_set.py"
    planted.write_text(
        "import threading\n\nclass Config:\n    def set(self, key, value):\n        pass\n\n"
        "def handler():\n    cancelled = threading.Event()\n    cancelled.set()\n"
        "    cfg = Config()\n    cfg.set('k', 'v')\n",
        encoding="utf-8",
    )
    assert find_write_verb_calls(tmp_path) == []


# -- review round 2, IMPORTANT 4: the three shapes rule 2 used to miss ----


def test_the_scan_catches_a_verb_reached_through_a_from_wing_parser_import(tmp_path):
    """`from wing_parser import net` binds `net` off the `wing_parser`
    PACKAGE, not off `wing_parser.net`, so the old table -- which keyed on
    an import path starting `wing_parser.net` -- held nothing at all and
    `net.write.push(...)` passed both rules untouched."""
    planted = tmp_path / "sneaky.py"
    planted.write_text(
        "from wing_parser import net\n\ndef go(host, leaves):\n"
        "    return net.write.push(host, leaves, confirm=True)\n",
        encoding="utf-8",
    )
    calls = find_write_verb_calls(tmp_path)
    assert len(calls) == 1 and ":4:" in calls[0] and "push" in calls[0], calls
    uses = find_write_verb_uses(tmp_path)
    assert len(uses) == 1 and "push" in uses[0], uses


def test_the_scan_catches_a_verb_reached_through_a_bare_import_wing_parser(tmp_path):
    """`import wing_parser` binds only the top package -- the old table
    ignored it, so the fully-spelled `wing_parser.net.write.push(...)` was
    invisible."""
    planted = tmp_path / "sneaky_top.py"
    planted.write_text(
        "import wing_parser\n\ndef go(host, leaves):\n"
        "    return wing_parser.net.write.push(host, leaves, confirm=True)\n",
        encoding="utf-8",
    )
    calls = find_write_verb_calls(tmp_path)
    assert len(calls) == 1 and ":4:" in calls[0] and "push" in calls[0], calls


def test_a_non_net_attribute_chain_off_the_same_binding_is_not_an_offence(tmp_path):
    """The other half: binding `wing_parser` must not make every `.set(...)`
    under it an offence. `wing_parser.config.set(...)` goes nowhere near
    the write path, and a scan that cried wolf would be turned off."""
    planted = tmp_path / "innocent.py"
    planted.write_text(
        "import wing_parser\n\ndef go():\n"
        "    return wing_parser.config.set('k', 'v')\n",
        encoding="utf-8",
    )
    assert find_write_verb_calls(tmp_path) == []
    assert find_write_verb_uses(tmp_path) == []


def test_a_nested_module_may_not_inherit_the_allow_list_by_its_name(tmp_path):
    """The allow-list is the TOP-LEVEL `ui/live_write.py`, keyed on the
    path relative to the scan root -- not on `path.name`, which would hand
    write rights to any `ui/<anything>/live_write.py` somebody added."""
    nested = tmp_path / "sub"
    nested.mkdir()
    (nested / "live_write.py").write_text(
        "from wing_parser.net import write\n\ndef go(host):\n"
        "    return write.set(host, '/ch/1/fdr', -6.0, confirm=True)\n",
        encoding="utf-8",
    )
    imports = find_write_imports(tmp_path, skip_allowed=True)
    assert len(imports) == 1 and "sub" in imports[0], imports
    calls = find_write_verb_calls(tmp_path, skip_allowed=True)
    assert len(calls) == 1 and "sub" in calls[0], calls


def test_the_top_level_allow_listed_file_is_still_allow_listed(tmp_path):
    """The other half of the path rule: `live_write.py` at the scan root
    keeps its narrowed rule 1 and its exemption from rule 2."""
    (tmp_path / "live_write.py").write_text(
        "from wing_parser.net import write\n\ndef go(host):\n"
        "    return write.set(host, '/ch/1/fdr', -6.0, confirm=True)\n",
        encoding="utf-8",
    )
    assert find_write_imports(tmp_path, skip_allowed=True) == []
    assert find_write_verb_calls(tmp_path, skip_allowed=True) == []
