def test_screenshot_flag_writes_pngs(tmp_path, qt_app, monkeypatch, vu_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser.ui.__main__ import main

    out = tmp_path / "shots"
    code = main(["--screenshot", str(out), str(vu_path)])
    assert code == 0
    names = {p.stem for p in out.glob("*.png")}
    assert {"doctor", "overview", "channels", "routing", "diff", "import_"} <= names
    assert all((out / f"{n}.png").stat().st_size > 1000
               for n in names)  # blank grabs are ~small; real frames are not
