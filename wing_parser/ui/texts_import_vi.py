"""Vietnamese mirror of `IMPORT_TEXTS` in `texts_import.py`.

Key and placeholder parity with the English table is enforced by a test.
"""

IMPORT_TEXTS_VI: dict[str, str] = {
    "vocabulary.title": "Từ vựng",
    "vocabulary.open_button": "Từ vựng…",
    "vocabulary.tab.sets": "Bộ",
    "vocabulary.tab.terms": "Từ khoá",
    "vocabulary.close": "Đóng",
    "vocabulary.col.label": "Nhãn",
    "vocabulary.col.kinds": "Loại",
    "vocabulary.col.nested": "Bộ lồng bên trong",
    "vocabulary.col.source": "Nguồn",
    "vocabulary.col.key": "Từ khoá",
    "vocabulary.col.match": "Cách khớp",
    "vocabulary.add": "Thêm…",
    "vocabulary.edit": "Sửa…",
    "vocabulary.delete": "Xoá",
    "vocabulary.reset": "Đặt lại mặc định",
    "vocabulary.dialog.name": "Tên",
    "vocabulary.dialog.label": "Nhãn",
    "vocabulary.dialog.kinds": "Loại",
    "vocabulary.dialog.sets": "Bộ",
    "vocabulary.dialog.ignore": "Bỏ qua từ khoá này (không có loại)",
    "vocabulary.dialog.match": "Cách khớp",
    "vocabulary.dialog.match.exact": "khớp nguyên cả đoạn",
    "vocabulary.dialog.match.word": "khớp nguyên từ bên trong một câu",
    "vocabulary.broken": "hỏng — {names} không còn tồn tại",
    "vocabulary.problems_header": (
        "Có vấn đề trong classifier.yaml (do sửa tay) — hãy sửa thẳng mục "
        "đó trong classifier.yaml, hoặc xoá nó tại đây bằng Xoá/Đặt lại "
        "mặc định nếu đã có dòng tương ứng:"
    ),
    "vocabulary.search_placeholder": "Tìm…",
    "vocabulary.source.default_deleted": "mặc định, đã xoá",
    "vocabulary.pick_set": "Chọn bộ khác…",
    "vocabulary.drop_reference": "Bỏ tham chiếu",
    "vocabulary.pick_set_prompt": "Chọn một bộ để thay cho {name}:",
    "vocabulary.no_sets_to_pick": "Không có bộ nào để chọn.",
    "vocabulary.name_required": "Tên không được để trống.",
    "vocabulary.name_exists": "đã tồn tại — hãy dùng Sửa",
    "vocabulary.write_failed": "Không lưu được: {error}",
    "vocabulary.kind_drop_confirm": (
        "Lưu sẽ bỏ các loại không xác định {kinds}, bản build này không "
        "nhận ra chúng. Tiếp tục?"
    ),
    "vocabulary.delete_confirm": (
        "Xoá {name}? Không thể hoàn tác từ đây."
    ),
    "vocabulary.overwrite_confirm": "{name} đã tồn tại — ghi đè?",
    "vocabulary.tab.assistant": "Trợ lý",
    "vocabulary.assistant.placeholder": (
        "vd. \"bộ trống của tôi không có kick out, thêm tom thứ hai\", "
        "\"cajon là percussion\""
    ),
    "vocabulary.assistant.propose": "Đề xuất",
    "vocabulary.assistant.cancel": "Huỷ",
    "vocabulary.assistant.apply": "Áp dụng các thay đổi đã tick",
    "vocabulary.assistant.running": "Đang hỏi model...",
    "vocabulary.assistant.cancelled": "Đã huỷ — chưa áp dụng gì.",
    "vocabulary.assistant.timeout": "Model không trả lời trong {seconds} s.",
    "vocabulary.assistant.busy": (
        "Đang có một yêu cầu tới model — hãy huỷ hoặc chờ."
    ),
    "vocabulary.assistant.col.apply": "",
    "vocabulary.assistant.col.before": "Trước",
    "vocabulary.assistant.col.after": "Sau",
    "vocabulary.assistant.col.reason": "Lý do",
    "vocabulary.assistant.no_key": (
        "Chưa cấu hình API key cho model — trợ lý cần có key. Đặt trong "
        "Cài đặt."
    ),
    "vocabulary.assistant.apply_result": "Đã áp dụng {applied}, lỗi {failed}.",
    "import.terms.key": "Từ khoá",
    "import.terms.match_word": "khớp bên trong một câu",
    "import.terms.ignore_remember": "Bỏ qua (ghi nhớ)",
    "import.terms.ai_propose": "AI: đề xuất cho các dòng chưa đọc",
    "import.terms.empty_key": (
        "Hãy nhập từ khoá trước khi ghi nhận — không bao giờ ghi giá trị "
        "trống."
    ),
    "import.terms.not_matching": (
        "Đã lưu, nhưng {fragment!r} vẫn không khớp với từ khoá của chính "
        "nó -- kiểm tra từ khoá hoặc ô \"khớp bên trong một câu\"."
    ),
    "import.scene.source": "Scene",
    "import.scene.source.doctor": "Scene của Doctor",
    "import.scene.source.file": "Mở .snap…",
    "import.scene.source.pull": "Lần Pull gần nhất của Console",
    "import.scene.open_file": "Mở .snap…",
    "import.scene.col.segment": "Đoạn",
    "import.scene.col.needed": "Loại cần có",
    "import.scene.col.found": "Đã thấy",
    "import.scene.col.missing": "Còn thiếu",
    "import.scene.skip": "Bỏ qua",
    "import.scene.continue": "Tiếp tục",
    "import.scene.no_scene": "Nguồn này chưa có scene nào được nạp.",
    "import.scene.no_pull_yet": "Lần chạy này chưa pull gì từ console.",
    "import.scene.file_error": "Không đọc được {path}: {error}",
    "import.scene.file_error_named": "Không đọc được file .snap đó: {error}",
    "import.step.scene": "Kiểm tra scene",
    "import.lint.title": "Kiểm tra file show-context",
    "import.lint.open": "Kiểm tra một file show-context có sẵn…",
    "import.lint.fix": "Sửa",
    "import.lint.close": "Đóng",
    "import.lint.confirm": (
        "Ghi các bản sửa vào file này? Một bản sao .bak được tạo trước."
    ),
    "import.lint.clean": "{count} đoạn, không có gì cần sửa.",
    "import.lint.fixed": "đã sửa {n} mục:",
    "import.lint.backup_failed": "Không ghi được bản sao lưu: {error}",
    "import.lint.read_failed": "Không đọc được {path}: {error}",
    "import.lint.repair_failed": (
        "Không ghi được các bản sửa (file .bak vẫn còn): {error}"
    ),
    "import.lint.fixable_mark": "[tự sửa được] {anomaly}",
    "import.lint.unfixable_mark": "[chỉ sửa tay] {anomaly}",
    "import.try_ai.button": "Thử AI trên file này",
    "import.try_ai.cancel": "Huỷ",
    "import.try_ai.running": "Đang hỏi model...",
    "import.try_ai.cancelled": "Đã huỷ.",
    "import.try_ai.timeout": "Model không trả lời trong {seconds} s.",
    "import.try_ai.busy": (
        "Đang có một yêu cầu tới model — hãy huỷ hoặc chờ."
    ),
    "import.try_ai.no_key": (
        "Chưa cấu hình API key cho model — Thử AI cần có key. Đặt trong "
        "Cài đặt."
    ),
    "import.try_ai.kill_switch": "AI đang bị tắt (WING_DISABLE_LLM).",
    "import.try_ai.result": "{provider}, {seconds}s",
    "import.try_ai.field.sheet": "sheet: {value}",
    "import.try_ai.field.header_row": "header_row: {value}",
    "import.try_ai.field.columns": "columns: {value}",
    "import.try_ai.field.headers": "headers: {value}",
    "import.try_ai.field.problems": "problems: {value}",
    "vocabulary.assistant.kill_switch": "AI đang bị tắt (WING_DISABLE_LLM).",
}
