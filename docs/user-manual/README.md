# Hướng dẫn sử dụng wing-parser

> Công cụ đọc, phân tích và tư vấn cho bàn mixer **Behringer WING** — dùng offline
> tại venue, hoặc kèm model AI (DeepSeek) khi có mạng.

**Phiên bản tài liệu:** 2026-08-24 · khớp `main` sau sub-project G2b

---

## Cài đặt

```bash
# Trong thư mục dự án
pip install -e .                # phần lõi — chạy 100% offline
pip install -e .[ingest]        # + đọc file Excel (cần cho showcontext import)
pip install -e .[llm]           # + Anthropic (nếu dùng Claude)
pip install -e .[llm-openai]    # + DeepSeek/OpenAI (khuyến nghị)
```

Chạy thử:

```bash
wing --version
wing net identity 192.168.128.28    # đọc console đang bật (thay IP của desk)
```

## Cấu hình model AI (tùy chọn)

Dán API key vào file `provider.yaml` ở thư mục gốc là xong — xem chi tiết
[04-cau-hinh-model.md](04-cau-hinh-model.md). Không có key thì mọi lệnh vẫn
chạy đủ, chỉ thiếu phần "đề xuất hộ".

## Các mục

| File | Nội dung |
|---|---|
| [01-doc-cue-sheet.md](01-doc-cue-sheet.md) | Đưa kịch bản chương trình (Excel) vào hệ thống — wizard tương tác, `--one-shot`, từ vựng |
| [02-phan-tich-scene.md](02-phan-tich-scene.md) | Phân tích scene: `analyze`, `channel`, `routing`, `diff`, `doctor`, `feedback` |
| [03-console-truc-tiep.md](03-console-truc-tiep.md) | Làm việc với mixer đang bật: `net identity/snapshot/get/set/toggle/push/watch` |
| [04-cau-hinh-model.md](04-cau-hinh-model.md) | `provider.yaml`, DeepSeek, tắt model bằng `WING_DISABLE_LLM` |

## Ứng dụng desktop (wing-ui)

Ngoài CLI, dự án có app desktop: `wing-ui user-files\example-Vu.snap`.
Sidebar bảy trang — **Doctor** (tư vấn), **Overview** (tổng quan),
**Channels**, **Routing**, **Diff** (so sánh hai scene), **Import**
(wizard đưa Excel vào), **Console** (kết nối console thật để đọc — còn ghi thì đi
từ nút Repair bên Doctor; xem
[03-console-truc-tiep.md](03-console-truc-tiep.md)) — cùng trang
**Settings** (dán API key riêng, nút Test connection). Mô tả đầy đủ
(verdict, repair, journal, đóng gói `.exe`) nằm ở mục
[Desktop app trong README](../../README.md#desktop-app).

Phím tắt trong app:

| Phím | Làm gì |
|---|---|
| `Ctrl+O` | Mở file `.snap` |
| `Ctrl+Shift+S` | Save As (luôn ghi file mới) |
| `Ctrl+Z` | Undo thay đổi gần nhất |
| `F5` | Phân tích lại scene đang mở |
| `Ctrl+1` … `Ctrl+7` | Nhảy tới trang 1–7 trong sidebar |
| `Esc` | Đóng hộp thoại đang mở |

## Nguyên tắc hoạt động (đọc 30 giây, hiểu mọi lệnh)

1. **Offline first** — venue hay mất mạng; mọi tính năng cốt lõi không cần mạng.
2. **Không bịa số liệu** — gì không đọc được sẽ thành comment hiện rõ, không im lặng.
3. **Song song với WING-Edit** — mọi thao tác với console sống đều không chiếm kết nối.
4. **Quyết định của ToanAZ** — mỗi rule tư vấn ghi rõ `source:` ai quyết và `rationale:` vì sao.
