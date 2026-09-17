"""Spec S8: the write path must be structurally unreachable from wing_parser/ui/.

Not a promise, a scan (S8.2). Two rules, each an `ast` walk over every
`.py` under `wing_parser/ui/`:

1. No import, static or dynamic, reaches `wing_parser.net.write` -- plain
   `import`/`from ... import` shapes, plus `importlib.import_module(...)`,
   `import_module(...)`, `__import__(...)` with a literal first argument
   naming it (or `wing_parser.net` with `write` in a `fromlist`, or the
   relative `".write"` against a literal `package`, which D-44 taught it
   to resolve). A computed name is a blind spot either way.
2. No write verb (`set`/`toggle`/`node_write`/`push`) is called on a name
   bound, in this module's own import table, from `wing_parser.net` --
   walked back through any `Attribute`/`Call` chain to its leftmost
   `Name`. Not bare-name matching: `self.cancel.set()`
   (`live_watch_session.py:143`) and `self._cancelled.set()`
   (`workers.py:69`), both `threading.Event`, end at `self`, unbound.

`Transport.client(host)` (used at `live_watch_session.py:87`) returns a
bare `WingClient`; rule 2 need not name it, since the four verbs are
module *functions* in `net/write.py`, not `WingClient` methods -- the
only real write through this seam, `write.node_write(client, ...)`,
needs an import that rule 1 already catches. Pinned by
`test_write_verbs_are_not_client_methods`, not just assumed.

Blind spot shared with `test_ui_texts.py`: a local variable assigned from
a net-bound call (`wc = client.WingClient(host)` then `wc.set(...)`) is
invisible to rule 2 -- only names bound directly by an `Import`/`ImportFrom`
are tracked; `client.WingClient(host).set(...)` in one expression IS caught.
"""
from __future__ import annotations

import ast
from importlib.util import resolve_name
from pathlib import Path

import wing_parser.ui as ui_package

UI_ROOT = Path(ui_package.__file__).resolve().parent

WRITE_VERBS = {"set", "toggle", "node_write", "push"}


def _py_files(root: Path):
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" not in path.parts:
            yield path


def _net_bound_names(tree: ast.Module) -> dict[str, str]:
    """Local names bound from `wing_parser.net` (Import/ImportFrom only)."""
    bound: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name == "wing_parser.net" or a.name.startswith("wing_parser.net."):
                    bound[a.asname or a.name.split(".")[0]] = a.name
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "wing_parser.net" or module.startswith("wing_parser.net."):
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


def find_write_imports(root: Path) -> list[str]:
    """Rule 1: every static or dynamic import reaching `wing_parser.net.write`."""
    offenders = []
    for path in _py_files(root):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)) and _import_reaches_write(node):
                offenders.append(f"{path}:{node.lineno}: imports the write path (wing_parser.net.write)")
            elif isinstance(node, ast.Call):
                name = _dynamic_call_reaches_write(node)
                if name:
                    offenders.append(f"{path}:{node.lineno}: {name}(...) reaches the write path (wing_parser.net.write)")
    return sorted(offenders)


def _base_name(node):
    """Walk an Attribute/Call chain down to its leftmost Name, or None."""
    while node is not None:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            node = node.value
        elif isinstance(node, ast.Call):
            node = node.func
        else:
            return None
    return None


def find_write_verb_calls(root: Path) -> list[str]:
    """Rule 2: a write-verb call whose base name is bound from `wing_parser.net`."""
    offenders = []
    for path in _py_files(root):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        net_bound = _net_bound_names(tree)
        for node in ast.walk(tree):
            if (not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute)
                    or node.func.attr not in WRITE_VERBS):
                continue
            base = _base_name(node.func.value)
            if base in net_bound:
                offenders.append(
                    f"{path}:{node.lineno}: calls .{node.func.attr}(...) on {base!r} (bound from {net_bound[base]})"
                )
    return sorted(offenders)


def test_no_ui_module_imports_the_write_path():
    offenders = find_write_imports(UI_ROOT)
    assert offenders == [], "the write path must not be importable from ui/:\n  " + "\n  ".join(offenders)


def test_no_ui_module_calls_a_write_verb_on_a_net_binding():
    offenders = find_write_verb_calls(UI_ROOT)
    assert offenders == [], "no write verb may be called on a net-bound name:\n  " + "\n  ".join(offenders)


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
