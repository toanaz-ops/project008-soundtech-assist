"""Every entry shipped in knowledge/library validates with zero errors."""

from pathlib import Path

from wing_parser.library import LibraryStore

ROOT = Path(__file__).resolve().parent.parent / "knowledge" / "library"


def test_shipped_entries_have_no_errors():
    problems = []
    for item in LibraryStore(ROOT).entries(include_retired=True):
        problems += [issue.format(item.id) for issue in item.issues if issue.level == "error"]
    assert problems == []


def test_every_manifest_diagram_exists_on_disk():
    import yaml
    manifest = yaml.safe_load((ROOT / "diagrams.yaml").read_text(encoding="utf-8"))
    for item in manifest["diagrams"]:
        for ext in ("svg", "png"):
            assert (ROOT / "media" / item["entry"] / f"{item['file']}.{ext}").is_file(), item
