# Wave 7 — Verdict summary (hướng 3, phần không cần gu) — 2026-11-09

**Vì sao:** hướng 3 (advisory theo gu của ToanAZ) là wave nội dung tiếp theo
(`docs/proposals/2026-11-09-wave6-decisions.md` Q6), nhưng mọi con số và `source:`
chặn ở 6 thẻ gu mix HW-191.Q1–Q6. Phần agent làm được mà không đoán gu: biến vòng
feedback có sẵn (`wing_parser/advisory/feedback.py`, nút verdict trong Doctor) thành
thứ ông **đọc được** — hiện chỉ thấy đếm từng rule một khi chọn finding. Prep doc
§4 ("báo cáo log verdict theo rule, gợi ý mẫu").

## Phạm vi

1. **Hàm thuần (không Qt)** `wing_parser/advisory/feedback_report.py`:
   `build_report(entries) -> list[RuleVerdicts]`, một dòng mỗi `rule_id`: số
   `correct` / `false-positive` / `irrelevant`, layer, các `note` không rỗng (mới
   nhất trước), lần ghi cuối. Sắp xếp: nhiều `false-positive` + `irrelevant` nhất
   lên đầu. Cờ `candidate` khi `false-positive + irrelevant >= 3` **và** lớn hơn
   `correct` — nghĩa là "đáng hỏi ông có muốn viết principle/supersedes không",
   KHÔNG tự đổi rule nào.
2. **UI:** Tools ▸ **Verdict summary** (EN) / **Tổng hợp đánh giá** (VI) mở một
   dialog chỉ đọc: bảng theo rule (cột: Rule, Layer, Correct, False positive,
   Irrelevant, Last, Candidate), chọn một dòng thì thấy các note. Log rỗng →
   một câu giải thích cách ghi verdict từ Doctor. Mọi chuỗi qua `texts*.py`
   (EN + VI), số dùng font mono như các bảng khác.
3. **Không** có nút ghi rule, không gọi model, không đụng bàn.

## Không làm

- Viết principle từ verdict (cần lời ông — HW-191.Q6).
- Học máy / tự động đổi severity.

## Kiểm

TDD cho `build_report` (đếm, sắp xếp, ngưỡng candidate, note rỗng bị bỏ, log
rỗng). Một test UI: dialog mở với log mẫu, đúng số dòng, chọn dòng hiện note; log
rỗng hiện câu hướng dẫn. Trần 200 dòng cho file UI.
