"""Vietnamese mirror of `texts_lang.LANG_TEXTS` (parity is tested)."""

LANG_TEXTS_VI: dict[str, str] = {
    "settings.language": "Ngôn ngữ",
    "lang.en": "English",
    "lang.vi": "Tiếng Việt",
    "settings.language_note": (
        "Restart wing to apply the new language. / "
        "Khởi động lại wing để áp dụng ngôn ngữ mới."
    ),
    "settings.language_run_hint": (
        "Lần chạy này đang hiển thị {language}. Lựa chọn đã lưu áp dụng "
        "từ lần khởi động sau."
    ),
    "settings.probe_replied": "{name} đã phản hồi",
    "ai_error.bad_key": (
        "Nhà cung cấp từ chối key này. Kiểm tra lại trong Cài đặt."
    ),
    "ai_error.quota": (
        "Nhà cung cấp báo hết hạn mức hoặc bị giới hạn tốc độ. "
        "Thử lại sau."
    ),
    "ai_error.no_key": "Chưa cấu hình API key. Thêm key trong Cài đặt.",
    "ai_error.no_network": (
        "Không kết nối được tới nhà cung cấp — kiểm tra mạng."
    ),
    "ai_error.sdk_missing": (
        "Bản build này chưa cài SDK model của nhà cung cấp đó."
    ),
    "ai_error.bad_reply": (
        "Không đọc được câu trả lời của model theo dạng mong đợi."
    ),
}
