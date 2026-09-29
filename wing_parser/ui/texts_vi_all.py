"""The merged Vietnamese table: the counterpart of `texts.TEXTS`."""

from wing_parser.ui.texts_console_vi import CONSOLE_TEXTS_VI
from wing_parser.ui.texts_import_vi import IMPORT_TEXTS_VI
from wing_parser.ui.texts_lang_vi import LANG_TEXTS_VI
from wing_parser.ui.texts_moved_vi import MOVED_TEXTS_VI
from wing_parser.ui.texts_vi import VI_TEXTS
from wing_parser.ui.texts_write_vi import WRITE_TEXTS_VI

VI: dict[str, str] = {
    **VI_TEXTS,
    **CONSOLE_TEXTS_VI,
    **WRITE_TEXTS_VI,
    **IMPORT_TEXTS_VI,
    **LANG_TEXTS_VI,
    **MOVED_TEXTS_VI,
}
