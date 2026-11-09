"""Bảng tiếng Việt của Automix: đối ứng với `texts_automix.py`."""

from __future__ import annotations

AUTOMIX_TEXTS_VI: dict[str, str] = {
    "menu.automix": "Tự động &mix...",
    "settings.automix": "Tự động mix",
    "settings.automix.disabled": "Tắt",
    "settings.automix.draft": "Chỉ bản nháp",
    "settings.automix.full_auto": "Tự động hoàn toàn (bàn trực tiếp)",
    "settings.automix_note": (
        "Chỉ bản nháp: Công cụ > Tự động mix đề xuất thay đổi cho từng "
        "kênh để bạn duyệt rồi áp vào scene đang mở. Không gửi gì ra desk. "
        "Chế độ tự động hoàn toàn còn có phần trực tiếp, liên tục đổi desk "
        "đang kết nối cho đến khi bạn bấm Dừng."),

    "automix.title": "Tự động mix (bản nháp)",
    "automix.banner": (
        "Chỉ là bản nháp: không gửi gì ra desk. Đây là giá trị mặc định "
        "theo sách vở, độ tin cậy thấp, theo thể loại đã chọn; chủ sở hữu "
        "phải duyệt từng thay đổi trước khi lưu."),
    "automix.propose": "Đề xuất",
    "automix.apply": "Áp vào scene (nháp)",
    "automix.confirm": (
        "Ghi {count} thay đổi vào scene đang mở dưới dạng bản nháp? Chưa "
        "lưu và chưa gửi gì cho đến khi bạn dùng Save as."),
    "automix.summary": (
        "{changes} thay đổi, {suggestions} gợi ý, {skipped} bỏ qua, "
        "giảm headroom {trim:.1f} dB, {warnings} cảnh báo tri thức"),
    "automix.genre": "Thể loại",
    "automix.bpm": "BPM",
    "automix.venue": "Không gian",
    "automix.strength": "Cường độ",
    "automix.stages": "Công đoạn",
    "automix.percent": "{value} %",

    "automix.genre.pop": "Pop",
    "automix.genre.rock": "Rock",
    "automix.genre.ballad": "Ballad",
    "automix.genre.jazz": "Jazz",
    "automix.genre.edm": "EDM",
    "automix.genre.bolero": "Bolero",
    "automix.genre.speech": "Hội nghị / lời nói",
    "automix.venue.small": "Nhỏ",
    "automix.venue.medium": "Vừa",
    "automix.venue.large": "Lớn",
    "automix.stage.hpf": "HPF",
    "automix.stage.eq": "EQ",
    "automix.stage.gate": "Gate",
    "automix.stage.comp": "Comp",
    "automix.stage.fader": "Fader",
    "automix.stage.fx": "FX",
    "automix.stage.sends": "Send",
    "automix.stage.inserts": "Insert",

    "automix.tab.changes": "Thay đổi",
    "automix.tab.suggestions": "Gợi ý",
    "automix.tab.skipped": "Bỏ qua",
    "automix.tab.warnings": "Cảnh báo",
    "automix.col.channel": "Kênh",
    "automix.col.source": "Nguồn",
    "automix.col.stage": "Công đoạn",
    "automix.col.parameter": "Tham số",
    "automix.col.before": "Trước",
    "automix.col.after": "Sau",
    "automix.col.confidence": "Độ tin cậy",
    "automix.col.text": "Gợi ý",
    "automix.col.reason": "Lý do",
    "automix.col.warning": "Cảnh báo",
    "automix.detail.sources": "Nguồn:",
    "automix.detail.no_sources": "Không có nguồn trích dẫn: mặc định kỹ thuật.",

    "automix.full_auto": "Tự động hoàn toàn...",
    "automix.col.path": "Tham số",
    "automix.col.mode": "Kết quả",
    "automix.live.title": "Tự động mix (hoàn toàn, bàn trực tiếp)",
    "automix.live.banner": (
        "Chế độ tự động hoàn toàn liên tục đổi desk đang kết nối, từng "
        "bước nhỏ, qua đúng đường ghi đã kiểm soát như Repair. Hãy Pull "
        "scene ở trang Console trước. Tham số bạn tự vặn sẽ bị khoá và "
        "được để yên. Mô phỏng (mặc định bật) chỉ đọc desk, không ghi."),
    "automix.live.ack": (
        "TỰ ĐỘNG HOÀN TOÀN: ứng dụng sẽ liên tục đổi desk này cho đến "
        "khi Dừng"),
    "automix.live.simulate": "Mô phỏng (không ghi)",
    "automix.live.confirm_real": (
        "Tắt Mô phỏng? Lần Bắt đầu tới sẽ ghi vào desk thật."),
    "automix.live.start": "Bắt đầu",
    "automix.live.stop": "Dừng (Esc)",
    "automix.live.revert": "Hoàn tác automix",
    "automix.live.locked": "Bị khoá do chỉnh tay (để yên):",
    "automix.live.need_connection": (
        "Hãy kết nối console trước (trang Console), rồi pull scene."),
    "automix.live.need_scene": "Hãy pull hoặc mở một scene trước (trang Console).",
    "automix.live.busy": "Đang có một lệnh ghi chạy; thử lại.",
    "automix.live.state.idle": "Chờ",
    "automix.live.state.running": "Đang chạy",
    "automix.live.state.stopped": "Đã dừng",
    "automix.live.state.failed": "Thất bại",
    "automix.live.status": (
        "{state} - lượt {ticks}, dòng {rows}, còn chờ {pending}, "
        "khoá {locked}"),
    "automix.live.mode.simulated": "Sẽ ghi",
    "automix.live.mode.sent": "Đã gửi",
    "automix.live.mode.clamped": "Bị kẹp",
    "automix.live.mode.no_reply": "Không phản hồi",
    "automix.live.mode.revert": "Đã hoàn tác",
    "automix.live.error": "Lỗi: {error}",
    "automix.live.gate_closed": (
        "Đã dừng: mất kết nối console hoặc mất trạng thái arm."),
    "automix.live.reverted": "Đã hoàn tác {count} tham số về giá trị cũ trên desk.",
    "automix.live.nothing_to_revert": "Không có gì để hoàn tác.",
    "automix.live.need_ack": "Hãy tick ô FULL AUTO trước, hoặc dùng Mô phỏng.",
    "automix.live.need_mode": (
        "Cài đặt > Automix chưa ở chế độ Full auto; đổi ở đó, hoặc dùng Mô phỏng."),
    "automix.live.gate_busy": (
        "Một lệnh ghi khác (Repair hoặc Hoàn tác) đang xếp hàng hoặc chạy; hãy chờ."),
    "automix.live.mode_off": (
        "Đã dừng: Cài đặt > Automix đã đổi khỏi Full auto."),
    "automix.live.reverted_skipped": (
        "Đã hoàn tác {count} tham số; bỏ qua {skipped} (chỉnh tay, bị khoá "
        "hoặc không đọc được)."),
}
