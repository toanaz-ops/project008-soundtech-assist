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

## Theo dõi thay đổi trực tiếp

```bash
wing net watch 192.168.128.28 --until 120    # theo dõi 120 giây rồi dừng
wing net watch 192.168.128.28 --json         # máy đọc được, Ctrl+C để dừng
wing net watch 192.168.128.28 --interval 0.5 # chủ động giãn chu kỳ poll
```

Đã đo trên console thật: ~150 sự kiện trong 120s, mỗi kéo fader từ WING-Edit
hiện sau ~250 ms; hai phần mềm đứng cạnh nhau không xung đột.

> Mẹo: nếu lần mở đầu `watch` báo thiếu cả family lá (unresolved families),
> **chạy lại** trước khi tin kết quả — lỗi tạm thời của quá trình dò schema,
> tool tự báo rõ chứ không giấu.
