"""One stylesheet, tokens, and a bundle-safe resource lookup."""


def test_resource_path_resolves_in_dev():
    from pathlib import Path

    from wing_parser.ui.theme import resource_path

    path = resource_path("theme.qss")
    assert path.exists()
    assert path == Path(path)  # sanity: it is a real path object
    assert "resources" in str(path)


def test_stylesheet_carries_tokens():
    from wing_parser.ui.theme import load_stylesheet

    qss = load_stylesheet()
    assert "#background" in qss or "@" in qss  # token markers survive
    assert len(qss) > 200
