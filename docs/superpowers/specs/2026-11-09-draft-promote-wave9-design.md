# Wave 9 — Promote a draft rule into principles.yaml — 2026-11-09

**Vì sao:** wave 8 cho ông chạy thử một rule nháp (`<knowledge_dir>/drafts/*.yaml`)
trên các scene thật. Bước còn lại là chép nháp đã duyệt vào `principles.yaml` — hiện
phải mở file bằng tay, dễ sai thụt lề YAML. Wave 9 là nút làm việc đó, **ông bấm**;
agent không bao giờ tự chép (prep doc §4 "không tự bật principle khi ông chưa duyệt").

## Quyết định (agent tự chốt)

- **P1 — Cổng:** chỉ chép khi `load_draft(...).promotable` (không lỗi, mọi rule có
  `source:` chứa `ToanAZ` + ngày ISO). Nút tắt và hiện lý do khi chưa đủ.
- **P2 — Giữ nguyên lời ông:** chép **entry YAML gốc** của nháp (dict đọc từ file
  nháp, giữ thứ tự khoá), không dựng lại từ `Rule`.
- **P3 — Không phá file đang có:** đọc `principles.yaml` dạng text. Nếu `principles:`
  rỗng (`[]` hoặc null) → thay dòng đó bằng `principles:` + các entry. Nếu đã có entry
  → nối các entry vào cuối, chỉ khi `principles:` là khoá cấp cao cuối cùng. Sau khi
  ghép, **parse lại** và kiểm danh sách = danh sách cũ + entry mới, đúng thứ tự; và
  `layers._as_rules(..., owner_source=True)` qua được trên bản ghép. Sai bất kỳ →
  không ghi gì, báo "bố cục principles.yaml lạ, hãy chép tay" kèm lỗi. Giữ nguyên
  comment đầu file. File chưa có → tạo với một dòng comment + `principles:`.
- **P4 — An toàn ghi:** chép `principles.yaml` → `principles.yaml.bak` (đè bản cũ,
  như Fix của lint W2), ghi bản ghép ra file tạm cùng thư mục rồi `os.replace`.
  UTF-8 tường minh. Rồi chuyển file nháp sang `drafts/promoted/<stem>-<YYYYMMDD-HHMM>.yaml`
  (không xoá) — `list_drafts` không thấy thư mục con nên nháp biến khỏi danh sách.
- **P5 — Sau khi chép:** hộp xác nhận nói rõ "rule sẽ chạy trong mọi lần Doctor";
  xong thì gọi `reanalyse` của cửa sổ chính nếu có scene đang mở, để Doctor phản
  ánh ngay; dialog nạp lại danh sách nháp.

## Phạm vi

1. Hàm thuần `wing_parser/advisory/draft_promote.py`:
   `promote(draft_path, directory=None, now=None) -> PromoteResult(ok, error,
   backup, moved_to, rule_ids)`. Không Qt.
2. UI: nút **Copy into principles.yaml…** / **Chép vào principles.yaml…** trong dialog
   dry-run (helper riêng `draft_promote_ui.py` để dialog ≤200 dòng), QMessageBox xác
   nhận, báo kết quả, callback `on_promoted` (opener truyền `window.reanalyse`).
3. Không: sửa/xoá principle đã có, gộp trùng, sinh nháp bằng AI.

## Kiểm

TDD: principles rỗng `[]`; principles có sẵn 1 entry + comment đầu file giữ nguyên;
file chưa có; nháp không promotable → từ chối, không file nào đổi; bố cục lạ (khoá
khác sau `principles:`) → từ chối, không ghi; `.bak` đúng nội dung cũ; nháp bị
chuyển sang `promoted/`; tiếng Việt trong `source:` còn nguyên sau ghi (UTF-8);
sau promote, `resolver.run` trên example-Vu.snap có finding của rule mới. UI: nút
tắt khi chưa promotable, bấm + xác nhận → file đổi + callback được gọi; Huỷ → không đổi.
