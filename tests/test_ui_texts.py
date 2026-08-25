"""Every UI string lives in one place for future language switching."""


def test_known_keys_resolve():
    from wing_parser.ui.texts import text

    assert text("app.title") == "wing"
    assert text("page.doctor") == "Doctor"
    assert text("page.overview") == "Overview"
    assert text("page.channels") == "Channels"
    assert text("page.routing") == "Routing"
    assert text("page.diff") == "Diff"
    assert text("page.import") == "Import"
    assert text("empty.open_hint")


def test_missing_key_is_loud():
    import pytest

    from wing_parser.ui.texts import text

    with pytest.raises(KeyError):
        text("no.such.key")
