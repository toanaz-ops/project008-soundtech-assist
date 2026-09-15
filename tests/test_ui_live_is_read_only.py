"""Spec S8: the write path must be structurally unreachable from wing_parser/ui/.

Not a promise, a scan (S8.2). Two independent rules, each an `ast` walk over
every `.py` under `wing_parser/ui/`:

1. **No import reaches `wing_parser.net.write`** -- `import
   wing_parser.net.write`, any alias of it, `from wing_parser.net import
   write`, or `from wing_parser.net.write import <anything>` are all the
   same violation: the write surface entering the package at all.
2. **No write verb is called on a name this module's own import table
   bound from `wing_parser.net`** -- a `Call` whose `func` is an
   `Attribute` named `set`/`toggle`/`node_write`/`push`, walked back
   through any `Attribute`/`Call` chain to its leftmost `Name`, checked
   against that Name's origin. Deliberately not bare-name matching:
   `self.cancel.set()` (a `threading.Event`, `live_watch_session.py:143`)
   and `self._cancelled.set()` (`workers.py:69`) both end at `self`, which
   no import binds, so neither trips rule 2 -- proven by
   `test_the_scan_ignores_an_unrelated_dot_set_call` below.

Known blind spot, same shape as `test_ui_texts.py`'s: a **local variable
assigned from a net-bound call** is invisible to rule 2. `wc =
client.WingClient(host)` then, on a later line, `wc.set(...)` -- `wc` is
never itself an import-table entry, only the intermediate expression was.
Only names bound directly by an `Import`/`ImportFrom` are tracked. A
same-expression chain IS caught: `client.WingClient(host).set(...)`
walks back through the `Call` and the `WingClient` `Attribute` to reach
`Name('client')`, which the import table does know.
"""
from __future__ import annotations

import ast
from pathlib import Path

import wing_parser.ui as ui_package

UI_ROOT = Path(ui_package.__file__).resolve().parent

WRITE_VERBS = {"set", "toggle", "node_write", "push"}


def _py_files(root: Path):
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" not in path.parts:
            yield path


def _net_bound_names(tree: ast.Module) -> dict[str, str]:
    """Local names this module's import table binds into `wing_parser.net`.

    Covers `import wing_parser.net.client as c` (name `c`), `from
    wing_parser.net import client` (name `client`), and `from
    wing_parser.net.client import WingClient` (name `WingClient`). Values
    are the dotted path bound, kept only so an offender message can say
    where a flagged name came from.
    """
    bound: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                dotted = alias.name
                if dotted == "wing_parser.net" or dotted.startswith("wing_parser.net."):
                    name = alias.asname or dotted.split(".")[0]
                    bound[name] = dotted
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "wing_parser.net" or module.startswith("wing_parser.net."):
                for alias in node.names:
                    bound[alias.asname or alias.name] = f"{module}.{alias.name}"
    return bound


def _import_reaches_write(node: ast.stmt) -> bool:
    if isinstance(node, ast.Import):
        return any(
            alias.name == "wing_parser.net.write"
            or alias.name.startswith("wing_parser.net.write.")
            for alias in node.names
        )
    if isinstance(node, ast.ImportFrom):
        module = node.module or ""
        if module == "wing_parser.net.write" or module.startswith("wing_parser.net.write."):
            return True
        if module == "wing_parser.net":
            return any(alias.name == "write" for alias in node.names)
    return False


def find_write_imports(root: Path) -> list[str]:
    """Rule 1: every Import/ImportFrom reaching `wing_parser.net.write`."""
    offenders = []
    for path in _py_files(root):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)) and _import_reaches_write(node):
                offenders.append(
                    f"{path}:{node.lineno}: imports the write path (wing_parser.net.write)"
                )
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
    """Rule 2: a set/toggle/node_write/push call whose base name is
    bound, in this module's own import table, from `wing_parser.net`."""
    offenders = []
    for path in _py_files(root):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        net_bound = _net_bound_names(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr not in WRITE_VERBS:
                continue
            base = _base_name(node.func.value)
            if base is not None and base in net_bound:
                offenders.append(
                    f"{path}:{node.lineno}: calls .{node.func.attr}(...) on "
                    f"{base!r} (bound from {net_bound[base]})"
                )
    return sorted(offenders)


def test_no_ui_module_imports_the_write_path():
    offenders = find_write_imports(UI_ROOT)
    assert offenders == [], "the write path must not be importable from ui/:\n  " + "\n  ".join(offenders)


def test_no_ui_module_calls_a_write_verb_on_a_net_binding():
    offenders = find_write_verb_calls(UI_ROOT)
    assert offenders == [], "no write verb may be called on a net-bound name:\n  " + "\n  ".join(offenders)


def test_the_scan_catches_a_planted_import(tmp_path):
    planted = tmp_path / "planted_write_import.py"
    planted.write_text(
        "from wing_parser.net import write\n"
        "\n"
        "def handler():\n"
        "    return write\n",
        encoding="utf-8",
    )
    offenders = find_write_imports(tmp_path)
    assert len(offenders) == 1
    assert str(planted) in offenders[0]
    assert ":1:" in offenders[0]


def test_the_scan_ignores_an_unrelated_dot_set_call(tmp_path):
    planted = tmp_path / "unrelated_dot_set.py"
    planted.write_text(
        "import threading\n"
        "\n"
        "class Config:\n"
        "    def set(self, key, value):\n"
        "        pass\n"
        "\n"
        "def handler():\n"
        "    cancelled = threading.Event()\n"
        "    cancelled.set()\n"
        "    cfg = Config()\n"
        "    cfg.set('k', 'v')\n",
        encoding="utf-8",
    )
    assert find_write_verb_calls(tmp_path) == []
