def test_screenshot_flag_writes_pngs(tmp_path, qt_app, monkeypatch, vu_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser.ui.__main__ import main

    out = tmp_path / "shots"
    code = main(["--screenshot", str(out), str(vu_path)])
    assert code == 0
    names = {p.stem for p in out.glob("*.png")}
    assert {"doctor", "overview", "channels", "routing", "diff", "import_"} <= names


def test_every_page_renders_in_the_house_palette(tmp_path, qt_app, vu_path,
                                                 monkeypatch):
    """The assertion that would have caught theme.apply() having no caller."""
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from PySide6.QtGui import QImage
    from wing_parser.ui.__main__ import main

    # Literal light-theme tokens until the NEXT task lands
    # tokens.COLOURS; that task swaps this set for set(tokens.COLOURS.values()).
    house = {0xFAFAFA, 0x1F1F1F, 0xF3F3F3, 0x0078D4}
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
