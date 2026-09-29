"""English strings for the language switch and the AI error classes.

Split out of `texts.py` (at its line ceiling). `ai_error.*` mirrors
`classifier/provider_errors._MESSAGES` word for word -- the CLI keeps the
originals, the UI looks these up so a Vietnamese run reads Vietnamese
(`ai_error_text.ai_message`); a test pins one key per non-OTHER code.
"""

LANG_TEXTS: dict[str, str] = {
    "settings.language": "Language",
    # Endonyms: each language names itself, in the same words either way.
    "lang.en": "English",
    "lang.vi": "Tiếng Việt",
    # Shown in BOTH languages on purpose: the reader just picked one of
    # them and cannot yet be assumed to read the other.
    "settings.language_note": (
        "Restart wing to apply the new language. / "
        "Khởi động lại wing để áp dụng ngôn ngữ mới."
    ),
    "settings.language_run_hint": (
        "This run is showing {language}. The saved choice applies from "
        "the next start."
    ),
    "settings.probe_replied": "{name} replied",
    "ai_error.bad_key": (
        "That key was rejected by the provider. Check it in Settings."
    ),
    "ai_error.quota": (
        "The provider reported no quota or a rate limit. Try again later."
    ),
    "ai_error.no_key": "No API key is configured. Add one in Settings.",
    "ai_error.no_network": "Could not reach the provider -- check the network.",
    "ai_error.sdk_missing": (
        "The model SDK for this provider is not installed in this build."
    ),
    "ai_error.bad_reply": (
        "The model's reply could not be read as the expected answer."
    ),
}
