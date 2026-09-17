# 03 — Làm việc với console đang bật

Mọi lệnh `net` chạy **song song** với WING-Edit và Companion — không chiếm
kết nối, không đá nhau (yêu cầu bắt buộc, đã nghiệm thu trên console thật
2026-08-23). IP mặc định của desk: `192.168.128.28`.

## Đọc

```bash
wing net identity 192.168.128.28     # tên, model, serial, firmware
wing net snapshot 192.168.128.28 -o show.snap   # đọc toàn bộ console ra file .snap
wing net get 192.168.128.28 /ch/01/fader        # đọc một lá đơn
```

> **Trên UI (wing-ui):** trang **Console** (Ctrl+7) có nút **Connect** —
> bấm vào là chạy đúng `wing net identity` (bắt tay hỏi tên desk), và nút
> **Pull** ở khối SNAPSHOT — chạy `wing net snapshot`, đọc cả console vào
> bộ nhớ rồi bấm **Export to .snap...** để ghi ra file, tương đương `-o`.
> Riêng `wing net get` — đọc một lá đơn — **chưa có nút trên UI ở wave 2
> này**: đây là việc chỉ CLI làm, vì UI cố tình chỉ đọc những gì cần cho
> luồng show (kết nối, dò schema, đọc cả console, theo dõi), không có ô
> tra một địa chỉ lẻ.

Sau khi có `.snap`, mọi lệnh ở [02](02-phan-tich-scene.md) dùng được ngay:
`wing doctor show.snap`.

## Ghi — luôn dry-run trước

```bash
wing net set 192.168.128.28 /ch/01/fader -12.5          # CHỈ HIỆN, chưa gửi gì
wing net set 192.168.128.28 /ch/01/fader -12.5 --confirm # mới gửi thật
wing net toggle 192.168.128.28 /ch/03/mute --confirm
wing net push 192.168.128.28 show.snap --confirm         # đẩy cả scene
```

Không có `--confirm` thì **không có gì được gửi** — an toàn để tập.

> **Trên UI:** `set`, `toggle`, `push` **không có nút nào cả**, cố ý — UI
> hiện tại chỉ đọc, không ghi (spec quyết định D1). Muốn ghi một tham số
> hay đẩy cả scene, vẫn phải ra CLI với `--confirm`.

## Theo dõi thay đổi trực tiếp

```bash
wing net watch 192.168.128.28 --until 120    # theo dõi 120 giây rồi dừng
wing net watch 192.168.128.28 --json         # máy đọc được, Ctrl+C để dừng
wing net watch 192.168.128.28 --interval 0.5 # chủ động giãn chu kỳ poll
```

> **Trên UI:** khối DISCOVERY có nút **Discover** — dò cây schema để dựng
> danh sách theo dõi (tương đương bước dò ngầm mà `wing net watch` tự làm
> trước khi poll); xong thì khối WATCH có nút **Start watch** — chạy
> đúng `wing net watch`, kết quả đổ thẳng vào bảng sự kiện trên trang
> thay vì in ra terminal. Không có ô gõ `--until`/`--json`; khoảng poll
> chỉnh bằng ô Interval bên cạnh nút.

Đã đo trên console thật: ~150 sự kiện trong 120s, mỗi kéo fader từ WING-Edit
hiện sau ~250 ms; hai phần mềm đứng cạnh nhau không xung đột.

> Mẹo: nếu lần mở đầu `watch` báo thiếu cả family lá (unresolved families),
> **chạy lại** trước khi tin kết quả — lỗi tạm thời của quá trình dò schema,
> tool tự báo rõ chứ không giấu.
