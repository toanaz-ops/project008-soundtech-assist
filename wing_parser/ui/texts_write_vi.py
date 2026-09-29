"""Vietnamese mirror of `WRITE_TEXTS` in `texts_write.py`.

Key and placeholder parity with the English table is enforced by a test.
Marks stay within what the vendored font carries: U+2713, U+00D7 and `!`.
"""

WRITE_TEXTS_VI: dict[str, str] = {
    # -- arming, once per connection -------------------------------------
    "console.write.arm_title": "Arm việc ghi vào console này",
    "console.write.reading": "Đang hỏi desk…",
    "console.write.desk": "{name} · {model} · serial {serial}",
    "console.write.identity_failed": (
        "Không nhận diện được desk tại {host}: {error} — chưa Arm."
    ),
    "console.write.latch": "Desk này hiện KHÔNG chạy show.",
    "console.write.latch_why": (
        "CLAUDE.md: không bao giờ ghi khi đang show nếu chưa có xác nhận "
        "rõ ràng."
    ),
    "console.write.name_prompt": "Gõ tên console này để xác nhận:",
    "console.write.name_wrong": "Đó không phải tên của console này.",
    "console.write.name_pending": "Đang chờ tên của console…",
    "console.write.arm": "Arm",
    "console.write.armed": "Đã Arm: {name}",
    "console.write.refused": "Bị từ chối: {error}",

    # -- the selector ----------------------------------------------------
    "console.write.level": "Áp dụng vào console",
    "console.write.manual": "Thủ công",
    "console.write.delayed": "Có độ trễ",
    "console.write.immediate": "Ngay lập tức",

    # -- the journal row's Send button -----------------------------------
    "console.write.send": "Gửi vào console",
    "console.write.blocked": "Hãy kết nối console (Ctrl+7) để gửi mục này.",
    "console.write.sending": "Đang gửi {address}…",
    "console.write.gate_closed": (
        "Kết nối tới console đã đứt. Chưa gửi gì."
    ),

    # -- the countdown ---------------------------------------------------
    "console.write.delay_title": "Sẽ áp dụng vào console sau {seconds} s",
    "console.write.address": "{address}",
    "console.write.countdown": "{remaining} s",
    "console.write.desk_value": "Desk hiện đang giữ: {value}",
    "console.write.file_value": "File scene mong đợi: {value}",
    "console.write.after": "Sẽ trở thành: {value}",
    "console.write.mismatch": (
        "! Desk đang giữ {desk}, file scene mong đợi {file}. Áp dụng sẽ "
        "ghi đè giá trị trên desk."
    ),
    "console.write.no_read": (
        "Desk không trả lời khi đọc địa chỉ này. Có thể nó không tồn tại "
        "ở đây."
    ),
    "console.write.apply_now": "Áp dụng ngay",
    "console.write.extend": "+5 s",
    "console.write.cancel": "Huỷ",
    "console.write.cancelled": (
        "Chưa áp dụng. Chỉnh sửa trong scene vẫn còn — dùng Hoàn tác để "
        "bỏ luôn cả nó."
    ),

    # -- the three outcomes ----------------------------------------------
    "console.write.sent": "đã gửi ✓ desk đang giữ {readback}",
    "console.write.clamped": (
        "! desk đang giữ {readback}, không phải {after} — console đã "
        "giới hạn giá trị."
    ),
    "console.write.no_reply": (
        "× {address}: desk không trả lời. "
        "Lệnh có thể đã tới desk, cũng có thể chưa."
    ),

    # -- the sent ledger -------------------------------------------------
    "console.write.sent_heading": "Đã gửi vào console",
    "console.write.ledger_row": "{address}: {desk!r} → {after!r}",
    "console.write.revert": "Revert",
    "console.write.revert_all": "Revert tất cả",
    "console.write.revert_stop": "Dừng",
    "console.write.reverting": "Đang revert {done}/{total}: {address}",
    "console.write.reverted": "đã revert ✓ desk đang giữ {readback}",
    "console.write.revert_stopped": (
        "Đã dừng sau {done}/{total}. Phần còn lại được giữ nguyên."
    ),
    "console.write.revert_cancelled": (
        "Chưa revert. Desk vẫn giữ giá trị đã ghi."
    ),
    "console.write.revert_unknown": (
        "Desk chưa từng báo giá trị trước đó, nên không có gì để trả lại."
    ),
    # `{plural:.0s}` renders empty: Vietnamese has no plural suffix, but the
    # placeholder must stay so both languages take the same arguments.
    "console.write.revert_skipped": (
        "Đã bỏ qua {skipped} dòng{plural:.0s}: desk chưa từng báo giá trị "
        "trước đó, nên không có gì để trả lại."
    ),
    "console.write.revert_failed": (
        "Lượt revert đã dừng: {error}. Phần còn lại được giữ nguyên."
    ),
}
