"""Show what a real show scene changed relative to the factory default."""

from pathlib import Path

from wing_parser import WingScene

REPO = Path(__file__).resolve().parents[1]


def main() -> None:
    factory = WingScene.load(REPO / "user-files" / "factory-scene.snap")
    show = WingScene.load(REPO / "user-files" / "example-Vu.snap")

    changes = factory.diff(show)
    print(f"{len(changes)} differences")

    faders = [c for c in changes if c.path.endswith(".fader_dB") and c.magnitude]
    print(f"\n{len(faders)} fader moves, largest first:")
    for change in sorted(faders, key=lambda c: -c.magnitude)[:10]:
        print(f"  {change.path:<24} {change.before} -> {change.after}")


if __name__ == "__main__":
    main()
