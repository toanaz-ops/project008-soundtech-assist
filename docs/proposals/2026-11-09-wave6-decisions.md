# Wave 6 — quyết định cho 7 câu của Fable (2026-11-09)

**Trạng thái:** lệnh tạm dừng 22/10 **đã gỡ** — chủ dự án 09/11/2026: "Kích hoạt
lại, bỏ lệnh tạm dừng các dự án" (chuyển qua phiên điều phối MASTER DEV0). Wave 6
mở; xong wave 6 thì đi tiếp wave sau, không chờ. Gu mix và nghiệm thu tại bàn vẫn
là của chủ dự án.

**Nguồn quyết định:** chủ dự án mở lại P008 ngày 09/11/2026 ("Còn dự án sound
asssistant sao không thấy chạy tiếp") với luật đứng "thấy có task chưa làm, cần
làm thì làm luôn". Phiên điều phối giao: chọn phương án **khuyến nghị** cho cả 7
câu trong `docs/proposals/2026-10-21-fable-options.md` §6 và ghi lại ở đây. Gu mix
và nghiệm thu trên bàn thật vẫn là của chủ dự án — không câu nào dưới đây quyết
thay ông về hai việc đó.

Ba nhóm:

| # | Câu | Quyết | Ai làm |
|---|-----|-------|--------|
| 1 | Khi nào WING-GIAQUY rảnh ~2 h? | **Hoãn cho chủ dự án** — chỉ ông biết lịch bàn. Thẻ manual trong Decision Box (gói nghiệm thu). | Chủ dự án |
| 2 | Immediate khi pre-flight read lỗi | **Từ chối** (như Delayed): không gửi gì, báo lỗi; không còn dòng sổ `desk_before=None` mới. | Agent — wave 6 |
| 3 | Ô "NOT running a show" | **Giữ ô tự khai + thêm cảnh báo mềm** khi Watch thấy fader/mute chuyển động trong 30 s gần nhất. Không chặn cứng. | Agent — wave 6 |
| 4 | PySide6 trong CI | **Ghim** cho check `test` + job `qt-latest` được phép đỏ. **Đã xong** ở PR #36 (`42ce6c8`), `ci/constraints-qt.txt`. | Đã xong |
| 5 | Encoding `.snap` tên tiếng Việt | **Hoãn tới buổi nghiệm thu**: cần 1 file `.snap` do WING-Edit lưu với tên có dấu + `probe13.json`. Không đoán encoding khi chưa có file thật. | Chủ dự án (tại bàn), agent sau đó |
| 6 | Wave content sau khi ký | **Hướng 3** (advisory mã hoá gu mix). Phần agent làm được offline thì làm ngay (xem dưới); phần số/`source:` **chặn ở 6 thẻ gu mix** trong Decision Box. | Agent (khung) + chủ dự án (nội dung) |
| 7 | Limiter model list (§5.3) | **Làm trong buổi nghiệm thu** (mở menu dyn model trên WING-Edit, ~5 phút). Bước trong thẻ manual. | Chủ dự án (tại bàn) |

## Wave 6 = phần agent làm được

1. **Q2 — Immediate từ chối khi pre-flight lỗi.** `ImmediateWrite`
   (`wing_parser/ui/write_router.py`) không còn `on_failure → _write(None)`;
   pre-flight lỗi gọi `on_error` với thông báo riêng, gate không nhận job, sổ
   không có dòng. Các chốt `desk_before is None` ở `changes_ledger` /
   `write_router` / `write_apply` giữ nguyên (dòng sổ cũ trong `.jsonl` vẫn có
   null). Đóng nửa sau D-52 #9.
2. **Q3 — cảnh báo mềm ở Arm.** Khi có phiên Watch và trong 30 s gần nhất có sự
   kiện fader/mute, hộp Arm hiện một dòng cảnh báo (EN + VI). Ô tick vẫn là
   chốt duy nhất; không chặn.
3. **Q6 (khung) — validator lớp `toanaz`.** Rule nằm trong
   `knowledge/toanaz/principles.yaml` hoặc `knowledge/toanaz/shows/*.yaml` phải
   có `source:` bắt đầu bằng `ToanAZ` và chứa ngày `YYYY-MM-DD` — chống rule
   "của ông" bịa mà không có lời ông (prep doc §4). Không thêm rule nào.
4. **Nợ agent-safe:** D-52 #3 (unit test `live_write.REAL._read`), D-52 #10
   (test Revert all chặt "cái sau không bắt đầu trước khi cái trước xong"),
   D-56 #6 (populate guard để lại dòng cũ), nếu đủ thời gian.

**Không mở hướng 3 phần nội dung (rule thật) khi 6 thẻ gu mix chưa có câu trả
lời.** Phiên sau đọc Decision Box nhóm "PROJECT008 Soundtech Assist" trước.

## Ghi chú

- Prep doc gu mix nói "5 câu ★" nhưng đánh ★ cho **6** câu (1, 4, 5, 6, 9, 11);
  Decision Box có 6 thẻ. Câu 6 tách đôi: nửa "cái gì là LỖI với IEM" là thẻ gu
  mix; nửa "danh sách limiter" là một bước trong thẻ manual nghiệm thu (= Q7).
- Exe phát hành dựng lại 2026-11-09 từ `main` `8a8370f` (PySide6 6.11.2):
  `dist\wing-ui.exe` 71.233.829 bytes, sống sau 8 s, zip
  `dist\wing-ui-20261109.zip`. Sẽ dựng lại lần nữa sau khi wave 6 merge.
