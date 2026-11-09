"""Bản tiếng Việt của `texts_log.py`. Danh từ mixer (Bus, Fader, Scene...)
giữ nguyên tiếng Anh như trên desk (B2)."""

from __future__ import annotations

LOG_TEXTS_VI: dict[str, str] = {
    "page.log": "Nhật ký",

    "log.shows_heading": "Các show",
    "log.entries_heading": "Các lần ghi",
    "log.export": "Xuất báo cáo…",
    "log.open_folder": "Mở thư mục nhật ký",
    "log.refresh": "Làm mới",
    "log.empty": (
        "Chưa có lần ghi nào. Các repair đã gửi xuống desk sẽ hiện ở đây."
    ),
    "log.pick_show": "Chọn một show ở bên trái.",
    "log.show_row": "{code}  {name}  {venue}",
    "log.show_counts": (
        "{first} – {last}  ·  {writes} lần ghi  ·  ✓ {sent}  ! {clamped}  × {no_reply}"
    ),
    "log.outcome.sent": "✓ đã ghi",
    "log.outcome.clamped": "! bị chặn",
    "log.outcome.no_reply": "× không trả lời",
    "log.warning.append_failed": (
        "Không lưu được nhật ký vào {folder}: {error}. "
        "Lần ghi xuống desk không bị ảnh hưởng."
    ),
    "log.warning.skipped": (
        "Đã bỏ qua {count} dòng không đọc được trong {code}."
    ),
    "log.save_title": "Xuất báo cáo",
    "log.save_filter": "Báo cáo HTML (*.html)",
    "log.export_done": "Đã lưu báo cáo: {path}",
    "log.export_failed": "Không lưu được báo cáo: {error}",

    "log.report.title": "Báo cáo ghi xuống desk",
    "log.report.show_code": "Mã show",
    "log.report.show": "Show",
    "log.report.venue": "Địa điểm",
    "log.report.dates": "Ngày",
    "log.report.desks": "Desk",
    "log.report.app": "Phiên bản app",
    "log.report.exported": "Xuất lúc",
    "log.report.summary": "Tóm tắt",
    "log.report.total": "Số lần ghi",
    "log.report.sent": "Đã xác nhận",
    "log.report.clamped": "Bị chặn",
    "log.report.no_reply": "Không trả lời",
    "log.report.reverts": "Số lần revert",
    "log.report.findings": "Finding đã xử lý",
    "log.report.col.time": "Thời gian",
    "log.report.col.desk": "Desk",
    "log.report.col.address": "Địa chỉ",
    "log.report.col.label": "Thay đổi",
    "log.report.col.finding": "Finding",
    "log.report.col.file_before": "File trước",
    "log.report.col.desk_before": "Desk trước",
    "log.report.col.written": "Đã ghi",
    "log.report.col.readback": "Đọc lại",
    "log.report.col.outcome": "Kết quả",
    "log.report.col.kind": "Loại",
    "log.report.kind.repair": "Repair",
    "log.report.kind.revert": "Revert",
    "log.report.footnote.sent": (
        "Desk đọc lại đúng giá trị đã ghi."
    ),
    "log.report.footnote.clamped": (
        "Desk trả về giá trị khác, tức là nó đã chặn hoặc từ chối giá trị "
        "vừa ghi."
    ),
    "log.report.footnote.no_reply": (
        "Desk không trả lời bước đọc lại. Lần ghi có thể đã vào hoặc chưa."
    ),

    # -- Tools > Tổng hợp đánh giá (wave 7) ---------------------------------
    "menu.verdicts": "&Tổng hợp đánh giá...",
    "verdicts.title": "Tổng hợp đánh giá",
    "verdicts.empty": (
        "Chưa có đánh giá nào. Trong Doctor, chọn một finding rồi bấm "
        "Đúng, Cảnh báo sai hoặc Không liên quan; bản tổng hợp sẽ hiện ở đây."
    ),
    "verdicts.col.rule": "Rule",
    "verdicts.col.layer": "Layer",
    "verdicts.col.correct": "Đúng",
    "verdicts.col.false_positive": "Cảnh báo sai",
    "verdicts.col.irrelevant": "Không liên quan",
    "verdicts.col.last": "Gần nhất",
    "verdicts.col.candidate": "Cần xét",
    "verdicts.candidate_yes": "Xem lại",
    "verdicts.notes_heading": "Ghi chú (mới nhất trước)",
    "verdicts.no_notes": "Rule này chưa có ghi chú.",

    # -- wave 8: chạy thử rule nháp ---------------------------------------
    "menu.dryrun": "Chạy thử rule &nháp...",
    "dryrun.title": "Chạy thử rule nháp",
    "dryrun.no_drafts": (
        "Chưa có rule nháp. Đặt file YAML nháp (cùng schema với "
        "principles.yaml, khoá `principles:`) vào:\n{path}"
    ),
    "dryrun.open_folder": "Mở thư mục",
    "dryrun.draft_label": "Nháp:",
    "dryrun.browse": "Chọn file…",
    "dryrun.browse_title": "Chọn file rule nháp",
    "dryrun.yaml_filter": "File YAML (*.yaml *.yml)",
    "dryrun.snap_filter": "Scene WING (*.snap)",
    "dryrun.rules": "{count} rule",
    "dryrun.ready": "Sẵn sàng chép sang principles.yaml",
    "dryrun.not_ready": "Chưa chép sang principles.yaml được:",
    "dryrun.scenes_heading": "Scene để chạy thử nháp",
    "dryrun.add": "Thêm…",
    "dryrun.add_title": "Thêm scene",
    "dryrun.remove": "Bỏ",
    "dryrun.run": "Chạy",
    "dryrun.no_change": "Nháp này không đổi gì trên các scene này.",
    "dryrun.col.scene": "Scene",
    "dryrun.col.before": "Trước",
    "dryrun.col.after": "Sau",
    "dryrun.col.added": "+Mới",
    "dryrun.col.removed": "\u2212Mất",
    "dryrun.col.error": "Lỗi",
    "dryrun.col.change": "Đổi",
    "dryrun.col.rule": "Rule",
    "dryrun.col.target": "Đích",
    "dryrun.col.message": "Nội dung",
}
