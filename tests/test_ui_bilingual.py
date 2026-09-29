"""English / Vietnamese string tables (docs/superpowers/specs/
2026-09-29-ui-bilingual-design.md): parity, fallback, resolution, glyphs.

Pure-logic tests plus the font check, which needs a QGuiApplication but
no window. The window-level tests live in `test_ui_bilingual_qt.py`.
"""

import string

import pytest

from wing_parser.ui import texts


def _pairs():
    """(name, English table, Vietnamese table) -- one row per source pair."""
    from wing_parser.ui.texts_console import CONSOLE_TEXTS
    from wing_parser.ui.texts_console_vi import CONSOLE_TEXTS_VI
    from wing_parser.ui.texts_import import IMPORT_TEXTS
    from wing_parser.ui.texts_import_vi import IMPORT_TEXTS_VI
    from wing_parser.ui.texts_lang import LANG_TEXTS
    from wing_parser.ui.texts_lang_vi import LANG_TEXTS_VI
    from wing_parser.ui.texts_moved import MOVED_TEXTS
    from wing_parser.ui.texts_moved_vi import MOVED_TEXTS_VI
    from wing_parser.ui.texts_vi import VI_TEXTS
    from wing_parser.ui.texts_write import WRITE_TEXTS
    from wing_parser.ui.texts_write_vi import WRITE_TEXTS_VI

    merged = {*CONSOLE_TEXTS, *IMPORT_TEXTS, *WRITE_TEXTS, *LANG_TEXTS,
              *MOVED_TEXTS}
    base = {k: v for k, v in texts.TEXTS.items() if k not in merged}
    return [
        ("base", base, VI_TEXTS),
        ("console", CONSOLE_TEXTS, CONSOLE_TEXTS_VI),
        ("import", IMPORT_TEXTS, IMPORT_TEXTS_VI),
        ("write", WRITE_TEXTS, WRITE_TEXTS_VI),
        ("lang", LANG_TEXTS, LANG_TEXTS_VI),
        ("moved", MOVED_TEXTS, MOVED_TEXTS_VI),
    ]


PAIRS = _pairs()
PAIR_IDS = [name for name, _, _ in PAIRS]


def _fields(value: str) -> list[tuple[str, str, str]]:
    """(name, conversion, spec) for every placeholder, sorted by name."""
    return sorted(
        (name, conv or "", spec or "")
        for _, name, spec, conv in string.Formatter().parse(value) if name)


def _drift(english: str, vietnamese: str) -> bool:
    """Same names and `!r`/`!s` conversions, per name. A format spec may
    differ ONLY where English has none and Vietnamese has `.0s` -- the
    idiom that swallows an English plural suffix (Vietnamese has none)."""
    en, vi = _fields(english), _fields(vietnamese)
    if [f[:2] for f in en] != [f[:2] for f in vi]:
        return True
    return any(e[2] != v[2] and not (e[2] == "" and v[2] == ".0s")
               for e, v in zip(en, vi))


@pytest.fixture
def language():
    """Set the UI language for one test; always back to English after."""
    yield texts.set_language
    texts.set_language("en")


@pytest.mark.parametrize("name,english,vietnamese", PAIRS, ids=PAIR_IDS)
def test_each_table_pair_has_identical_keys(name, english, vietnamese):
    assert set(english) == set(vietnamese), (
        f"{name}: only in EN {sorted(set(english) - set(vietnamese))}, "
        f"only in VI {sorted(set(vietnamese) - set(english))}")


@pytest.mark.parametrize("name,english,vietnamese", PAIRS, ids=PAIR_IDS)
def test_each_key_has_the_same_placeholders_in_both_languages(
        name, english, vietnamese):
    drift = {key: (_fields(english[key]), _fields(vietnamese[key]))
             for key in english if _drift(english[key], vietnamese[key])}
    assert drift == {}


@pytest.mark.parametrize("english,vietnamese,drifts", [
    ("{n} rows", "{n} dòng", False),
    ("{n!r} rows", "{n} dòng", True),            # conversion dropped
    ("{n} rows", "{n!r} dòng", True),            # conversion added
    ("{n} rows", "{m} dòng", True),              # different name
    ("{n:.2f} s", "{n:.1f} s", True),            # spec changed
    ("{n:.2f} s", "{n} s", True),                # spec dropped
    ("row{plural}", "dòng{plural:.0s}", False),  # the plural idiom
    ("row{plural:.0s}", "dòng{plural}", True),   # ... only one way round
    ("{a} {b}", "{b} {a}", False),               # reordering is fine
])
def test_the_placeholder_check_itself_catches_what_it_should(
        english, vietnamese, drifts):
    assert _drift(english, vietnamese) is drifts


def test_the_pairs_cover_every_english_key():
    """The split above must not silently drop a key from the comparison."""
    covered = {key for _, english, _ in PAIRS for key in english}
    assert covered == set(texts.TEXTS)


def test_the_merged_tables_have_the_same_keys():
    assert set(texts.VI) == set(texts.TEXTS)


def test_every_vietnamese_value_formats_with_dummy_arguments():
    """A stray brace or a bad spec is a ValueError at a show, not here."""
    for key, value in texts.VI.items():
        kwargs = {}
        for _, name, spec, _conv in string.Formatter().parse(value):
            if name:
                kwargs[name] = 1.5 if spec.endswith("f") else "x"
        try:
            value.format(**kwargs)
        except (KeyError, ValueError, IndexError) as exc:
            pytest.fail(f"{key!r}: {value!r} -> {exc!r}")


# -- selection and fallback ---------------------------------------------


def test_english_is_the_default_language():
    assert texts.current_language() == "en"
    assert texts.text("page.overview") == "Overview"


def test_set_language_switches_the_answer(language):
    language("vi")
    assert texts.current_language() == "vi"
    assert texts.text("page.overview") == texts.VI["page.overview"]
    assert texts.text("page.overview") != texts.TEXTS["page.overview"]


def test_an_unknown_language_reads_as_english(language):
    language("vi")
    language("klingon")
    assert texts.current_language() == "en"
    assert texts.text("page.overview") == "Overview"


def test_a_key_missing_from_vietnamese_falls_back_to_english(
        language, monkeypatch):
    monkeypatch.setitem(texts.TEXTS, "test.only_in_english", "English only")
    language("vi")
    assert texts.text("test.only_in_english") == "English only"


def test_a_key_in_neither_language_still_raises(language):
    language("vi")
    with pytest.raises(KeyError):
        texts.text("no.such.key")


# -- __main__ resolution ---------------------------------------------------


@pytest.mark.parametrize("flag,saved,expected", [
    ("vi", "en", "vi"), ("en", "vi", "en"), (None, "vi", "vi"),
    (None, "en", "en"), (None, "", "en"),
])
def test_the_flag_beats_the_saved_language(flag, saved, expected):
    from wing_parser.ui.__main__ import resolve_language

    assert resolve_language(flag, saved) == expected


# -- AI error classes (B8) -------------------------------------------------


def test_every_classified_ai_error_has_a_ui_text_in_both_languages():
    """A new provider_errors code must not reach the UI without a key."""
    from wing_parser.classifier import provider_errors

    codes = set(provider_errors._MESSAGES)
    assert codes, "provider_errors._MESSAGES is empty -- the test is blind"
    for code in codes:
        assert f"ai_error.{code}" in texts.TEXTS, code
        assert f"ai_error.{code}" in texts.VI, code


def test_ai_message_translates_a_class_and_keeps_the_provider_text_for_other(
        language):
    from wing_parser.ui.ai_error_text import ai_message

    language("vi")
    assert ai_message("bad_key", "english") == texts.VI["ai_error.bad_key"]
    assert ai_message("other", "HTTP 500: boom") == "HTTP 500: boom"
    language("en")
    assert ai_message("bad_key", "x") == texts.TEXTS["ai_error.bad_key"]


def test_the_english_ai_error_keys_match_the_cli_wording():
    from wing_parser.classifier import provider_errors

    for code, message in provider_errors._MESSAGES.items():
        assert texts.TEXTS[f"ai_error.{code}"] == message


# -- glyph coverage of the vendored fonts (B9) ----------------------------


def _non_ascii(table) -> set[str]:
    return {ch for value in table.values() for ch in value if ord(ch) > 127}


def test_the_vendored_fonts_draw_every_vietnamese_character(qt_app):
    """D-51: a glyph the font lacks renders as a box -- or a per-machine
    fallback. Vietnamese adds no NEW gap: whatever the fonts lack must
    already be in the English table (U+25CF, the Console lamp).

    Body faces (Plex Sans/Mono) must cover every non-ASCII character;
    Saira Condensed only sets headings and the sidebar (upper-cased), so
    it must cover the letters, upper-cased too, but not marks like the
    U+2713 check that only the Plex faces carry.
    """
    pytest.importorskip("PySide6.QtGui")
    from PySide6.QtGui import QRawFont

    from wing_parser.ui.theme.paths import resource_path

    fonts = resource_path("fonts")
    vietnamese = _non_ascii(texts.VI)
    english = _non_ascii(texts.TEXTS)
    letters = {ch for ch in vietnamese if ch.isalpha()}
    assert letters, "no Vietnamese letters seen -- the test is blind"
    letters |= {ch.upper() for ch in letters}

    def missing(face: str, chars: set[str]) -> set[str]:
        raw = QRawFont(str(fonts / face), 12)
        assert raw.isValid(), face
        return {ch for ch in chars if not raw.supportsCharacter(ord(ch))}

    gaps = {}
    for face in ("IBMPlexSans-Regular.ttf", "IBMPlexMono-Regular.ttf",
                 "IBMPlexMono-Medium.ttf"):
        gaps[face] = missing(face, vietnamese | letters) - english
    for face in ("SairaCondensed-SemiBold.ttf", "SairaCondensed-Bold.ttf"):
        gaps[face] = missing(face, letters)
    assert {f: "".join(sorted(g)) for f, g in gaps.items() if g} == {}
