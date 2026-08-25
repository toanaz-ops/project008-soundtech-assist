# 02 — Phân tích scene

Scene = toàn bộ trạng thái mixer, đọc từ file `.snap` hoặc từ console đang bật.
Chưa có file `.snap`? Lấy một cái trong 10 giây:
`wing net snapshot 192.168.128.28 -o show.snap` (xem [03](03-console-truc-tiep.md)).
Các ví dụ dưới dùng `show.snap` làm tên đại diện — thay bằng tên file của anh.

## `analyze` — nhìn tổng quan

```bash
wing analyze show.snap                  # từ file
wing analyze --live 192.168.128.28      # từ console đang bật
```

## `channel` — chi tiết một kênh

```bash
wing channel show.snap 12
```

## `routing` — sơ đồ routing

```bash
wing routing show.snap
```

Cho biết kênh nào route đi đâu, orphan nào chưa gắn, kênh nào chưa phân loại.

## `diff` — so sánh hai trạng thái

```bash
wing diff truoc.snap sau.snap                 # hai file
wing diff --live-before 192.168.128.28 sau.snap   # console trước ↔ file sau
wing diff --live-before IP1 --live-after IP2      # console ↔ console
```

Dùng để soi xem ai/kéo gì trên console giữa hai thời điểm. Mặc định hiện tối đa
50 khác biệt (`--limit 100` để tăng).

## `doctor` — rule tư vấn của ToanAZ

```bash
wing doctor show.snap                          # rule cơ bản (G-series…)
wing doctor --show show.yaml show.snap         # kèm show context → thêm rule Q1–Q7
wing doctor --profile small.yaml show.snap     # áp profile từ knowledge/toanaz/shows/
wing doctor --json show.snap > findings.json   # máy đọc được
```

Mỗi finding ghi rõ rule nào, vì sao (`rationale:`), ai quyết (`source:`).

## `feedback` — dạy lại tool khi nó nói sai

```bash
wing feedback "G8:ch.8.send.8" --verdict false-positive --scene show.snap --note "IEM được bảo vệ"
```

Verdict: `correct` / `false-positive` / `irrelevant`. Verdict được ghi nhớ — lần
sau rule đó không nhắc lại kiểu này nữa.
