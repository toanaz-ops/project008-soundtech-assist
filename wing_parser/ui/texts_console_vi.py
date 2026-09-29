"""Vietnamese mirror of `CONSOLE_TEXTS` in `texts_console.py`.

Key and placeholder parity with the English table is enforced by a test.
"""

CONSOLE_TEXTS_VI: dict[str, str] = {
    "console.address": "Console",
    "console.address_hint": "Địa chỉ IP hoặc hostname",
    "console.connect": "Kết nối",
    "console.disconnect": "Ngắt kết nối",
    "console.cancel": "Huỷ",
    "console.lamp": "●",
    "console.identity": "{name} · {model} · firmware {firmware}",
    "console.connecting": "Đang hỏi {host} xem nó là máy nào...",
    "console.cancelled": "Đã huỷ — chưa đọc gì.",
    "console.timeout": (
        "{host} không trả lời trong {seconds} s — kiểm tra địa chỉ và "
        "xem desk có nằm trong mạng này không."
    ),
    "console.failed": "Không kết nối được {host}: {error}",
    "console.busy": "Đang có một lệnh gọi console — hãy huỷ hoặc chờ.",
    "console.no_address": "Hãy nhập địa chỉ console trước — một IP hoặc một tên.",
    "console.discovery": "Dò schema",
    "console.discover": "Dò",
    "console.rerun": "Dò lại",
    "console.discovering": "Đang duyệt cây schema...",
    "console.walk_cancelled": "Đã huỷ — chưa duyệt gì.",
    "console.walk_timeout": (
        "{host} không trả lời trong {seconds} s khi đang duyệt schema."
    ),
    "console.walk_busy": (
        "Đang có một lượt duyệt schema — hãy huỷ hoặc chờ."
    ),
    "console.walk_failed": "Không duyệt được schema tại {host}: {error}",
    "console.inventory": "{total} leaf ({breakdown})",
    "console.unresolved_banner": (
        "Chưa xác định: {families} — sẽ theo dõi {total} leaf; hãy dò "
        "lại trước khi tin rằng danh sách này nhỏ."
    ),
    "console.snapshot": "Snapshot",
    "console.pull": "Pull",
    "console.pulling": "Đang đọc toàn bộ console từ {host}...",
    "console.pull_cancelled": "Đã huỷ — chưa pull gì.",
    "console.pull_timeout": (
        "{host} không trả lời trong {seconds} s khi đang pull scene."
    ),
    "console.pull_busy": (
        "Đang có một lượt đọc console — hãy huỷ hoặc chờ."
    ),
    "console.pull_failed": "Không pull được scene từ {host}: {error}",
    "console.incomplete_banner": (
        "{report} — scene đã nạp và dùng được, nhưng chưa phải toàn bộ desk."
    ),
    "console.scene_loaded": "Đã nạp scene — {findings} phát hiện.",
    "console.open_doctor": "Mở Doctor",
    "console.export": "Xuất ra .snap...",
    "console.export_title": "Xuất scene vừa pull",
    "console.exported": "Đã xuất ra {file}",
    "console.export_failed": "Không ghi được {file}: {error}",
    "console.watch": "Theo dõi",
    "console.start": "Bắt đầu theo dõi",
    "console.stop": "Dừng",
    "console.reconnect": "Kết nối lại",
    "console.interval": "Chu kỳ",
    "console.interval_suffix": " s",
    "console.col.time": "Thời gian (s)",
    "console.col.strip": "Strip",
    "console.col.key": "Key",
    "console.col.change": "Thay đổi",
    # Two value cells, formatted where every other value cell is: a
    # repr, so "0" and 0 never read the same.
    "console.event_time": "{seconds:.2f}",
    "console.event_change": "{before!r} → {after!r}",
    "console.watching": "Đang theo dõi {host} — {total} leaf.",
    "console.watch_rate": "{rate:.2f} sự kiện/s · đã chạy {elapsed:.1f} s",
    "console.stopping": "Đang dừng — việc theo dõi kết thúc sau vòng này.",
    "console.watch_stopped": (
        "Đã kết thúc theo dõi — {events} sự kiện qua {rounds} vòng."
    ),
    "console.watch_cancelled": (
        "Đã dừng theo dõi — các sự kiện ở trên vẫn được giữ lại."
    ),
    "console.watch_lost": (
        "Mất kết nối {host}: {error} — các sự kiện ở trên là thật. Hãy "
        "kết nối lại để tiếp tục."
    ),
    "console.watch_failed": (
        "Theo dõi lỗi trên {host}: {error} — không phải do desk im lặng. "
        "Các sự kiện ở trên là thật; hãy kết nối lại để tiếp tục."
    ),
    "console.no_watch_list": (
        "Hãy dò console trước — theo dõi cần danh sách leaf."
    ),
}
