"""Print an overview of the sample show scene."""

from pathlib import Path

from wing_parser import WingScene

REPO = Path(__file__).resolve().parents[1]


def main() -> None:
    scene = WingScene.load(REPO / "user-files" / "example-Vu.snap")
    print(f"{scene.path.name}: {scene.version.label}")

    for channel in scene.channels():
        if not channel.name.strip():
            continue
        guess = channel.source_type
        print(
            f"{channel.number:>3}  {channel.name:<20} "
            f"{guess.kind:<28} {guess.confidence:.2f}"
        )

    scene.classifier.flush()


if __name__ == "__main__":
    main()
