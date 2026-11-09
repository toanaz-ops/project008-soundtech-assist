"""Bảng tiếng Việt của Automix: đối ứng với `texts_automix.py`."""

from __future__ import annotations

AUTOMIX_TEXTS_VI: dict[str, str] = {
    "menu.automix": "Tự động &mix...",
    "settings.automix": "Tự động mix",
    "settings.automix.disabled": "Tắt",
    "settings.automix.draft": "Chỉ bản nháp",
    "settings.automix_note": (
        "Chỉ bản nháp: Công cụ > Tự động mix đề xuất thay đổi cho từng "
        "kênh để bạn duyệt rồi áp vào scene đang mở. Không gửi gì ra desk."),

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
}
