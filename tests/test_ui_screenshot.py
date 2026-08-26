def test_screenshot_flag_writes_pngs(tmp_path, qt_app, monkeypatch, vu_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser.ui.__main__ import main

    out = tmp_path / "shots"
    code = main(["--screenshot", str(out), str(vu_path)])
    assert code == 0
    names = {p.stem for p in out.glob("*.png")}
    assert {"doctor", "overview", "channels", "routing", "diff", "import_"} <= names


def test_screenshot_captures_the_diff_page_twice_for_the_bar_review(
        tmp_path, qt_app, monkeypatch, vu_path):
    """The A/B pair ToanAZ reviews the magnitude bar with: diff.png as
    shipped, diff-b.png with the bar forced off."""
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser.ui import diff_page
    from wing_parser.ui.__main__ import main

    out = tmp_path / "shots"
    assert main(["--screenshot", str(out), str(vu_path)]) == 0
    assert (out / "diff.png").exists()
    assert (out / "diff-b.png").exists()
    assert diff_page.SHOW_MAGNITUDE_BAR is True, "the flag must be restored"
    # An identical pair reviews nothing: the bar must actually show in
    # the "on" capture, so the table is seeded before both grabs.
    assert (out / "diff.png").read_bytes() != (out / "diff-b.png").read_bytes(), (
        "diff-a and diff-b must differ, or the A/B reviews nothing"
    )


def test_every_page_renders_in_the_house_palette(tmp_path, qt_app, vu_path,
                                                 monkeypatch):
    """The assertion that would have caught theme.apply() having no caller."""
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from PySide6.QtGui import QImage
    from wing_parser.ui.__main__ import main
    from wing_parser.ui.theme import tokens

    house = set(tokens.COLOURS.values())
    out = tmp_path / "shots"
    assert main(["--screenshot", str(out), str(vu_path)]) == 0
    for key in ("doctor", "overview", "channels", "routing", "diff", "import_"):
        image = QImage(str(out / f"{key}.png"))
        assert not image.isNull()
        assert (image.width(), image.height()) == (1280, 760)
        # Every pixel, straight from the byte buffer: house-coloured
        # glyph cores cover well under one percent of a frame, so no
        # sparse grid can be trusted to land on them.
        argb = image.convertToFormat(QImage.Format.Format_RGBA8888)
        raw = argb.constBits().tobytes()
        sampled = {raw[i] << 16 | raw[i + 1] << 8 | raw[i + 2]
                   for i in range(0, len(raw), 4)}
        assert len(sampled) >= 3, f"{key}.png is one flat colour"
        assert len(sampled & house) >= 2, f"{key}.png carries no house token"
