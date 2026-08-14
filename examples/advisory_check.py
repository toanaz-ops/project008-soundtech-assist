"""Run the advisory rules and show which layer decided each finding."""

from pathlib import Path

from wing_parser import WingScene

REPO = Path(__file__).resolve().parents[1]


def main() -> None:
    scene = WingScene.load(REPO / "user-files" / "example-Vu.snap")

    print("active rules:")
    for rule in scene.advisory.rules():
        print(f"  {rule.id:<8} [{rule.layer}] {rule.title}")

    suppressed = scene.advisory.suppressed()
    for rule_id, by in suppressed.items():
        print(f"  {rule_id:<8} suppressed by {by}")

    print("\nfindings:")
    for finding in scene.advisory.run():
        print(f"  [{finding.severity}] {finding.rule_id} at {finding.target} via {finding.layer}")
        print(f"      {' '.join(finding.message.split())}")

    scene.classifier.flush()


if __name__ == "__main__":
    main()
