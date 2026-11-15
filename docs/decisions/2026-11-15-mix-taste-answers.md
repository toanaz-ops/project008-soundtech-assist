# Gu mix (hướng 3) — câu trả lời của ToanAZ cho HW-191.Q1–Q6

Ghi ngày 2026-11-15. Chủ dự án trả lời 6 thẻ gu mix trong Hộp quyết định AZ ngày
2026-11-11; chưa phiên nào xử lý tới 15/11. Câu hỏi gốc:
`docs/proposals/2026-10-22-mix-taste-prep.md` §2 (câu ★ 1, 4, 5, 6, 9, 11).

**Kết quả chung:** Q1–Q5 anh chọn **tự cho số**, không giữ nguyên theo sách. Q6 anh chọn
ghi dần qua verdict bar, kèm lời nhắn *"Thử kể xem"* (agent đưa ví dụ để anh xác nhận).
Agent **không đoán số thay anh**. Mọi dữ liệu anh cần cho được gộp vào **một** thẻ việc
tay **HW-256** trong Hộp quyết định (mỗi câu một bước, có giá trị mặc định hiện tại và mã
ngắn K1, V2, G3… để anh trả lời nhanh). Tới khi HW-256 có trả lời, hành vi của tool
**không đổi**.

## Quyết định

| Thẻ | Câu hỏi | Anh chọn | Nghĩa là | Khi có số, ghi vào đâu |
|---|---|---|---|---|
| HW-191.Q1 | Trong `.snap` tin giá trị nào? | **B** — anh liệt kê tham số bỏ qua (vd gain, fader) | Hiện chưa rule nào chấm số gain hay fader, nên đây không phải `supersedes`: nó giới hạn rule tương lai (gồm rule gain staging của Q5) được đọc tham số nào từ `.snap` | `knowledge/toanaz/principles.yaml` (ghi chú + điều kiện cho rule mới) |
| HW-191.Q2 | Kick: HPF, gate/comp, cấu hình "sai" | **B** — anh cho số riêng | PB5 (sách) được thay bằng số của anh | `principles.yaml` (supersedes PB5) + `knowledge/toanaz/automix.yaml` |
| HW-191.Q3 | Vocal lead / MC: HPF, comp, de-ess, fader | **B** — anh cho số riêng, có thể tách MC và ca sĩ | S1 / PC1..PC8 (sách) được thay ở chỗ số anh khác | `principles.yaml` + `automix.yaml` (`speech.vocal`, `speech.mc`) |
| HW-191.Q4 | IEM: cái gì là LỖI | **B** — anh liệt kê lỗi bắt buộc + severity | G7..G10 được viết lại theo mức của anh. Danh sách model limiter cho G7 vẫn ở thẻ HW-254 | `principles.yaml` (hoặc `shows/<name>.yaml` nếu chỉ đúng một loại show) |
| HW-191.Q5 | Mục tiêu gain staging | **B** — anh cho số | Rule mới kiểm peak input / headroom master (hiện chưa có rule nào). `.snap` không lưu meter (AM-23), nên mục tiêu peak chỉ kiểm được trên bàn đang chạy (Watch) | `automix.yaml` (`balance.headroom`) + rule mới |
| HW-191.Q6 | 3 cảnh tool bắn vô lý | **A** — ghi dần qua verdict bar trong Doctor mỗi show (note 1 câu). Ghi chú anh: *"Thử kể xem"* | Agent đưa 5 cảnh nghi vô lý (dưới) để anh xác nhận; sau đó anh tiếp tục ghi dần bằng verdict bar | Cảnh anh xác nhận → `applies_when` / `supersedes` trong `principles.yaml` hoặc `shows/<name>.yaml`; verdict hằng ngày → `knowledge/toanaz/feedback.jsonl` |

## Luật khi nạp câu trả lời

- Mỗi rule/override lớp anh phải có `source:` chứa `ToanAZ` + ngày ISO `YYYY-MM-DD`
  (validator wave 6, `wing_parser/advisory/validation.py`; cùng luật cho `automix.yaml`).
  Ngày ghi là ngày anh trả lời HW-256.
- Giá trị in sẵn trong HW-256 là số **sách / mặc định kỹ thuật đang chạy**, không phải
  số của anh. Agent chỉ ghi một số thành rule của anh khi anh **viết rõ** ở bước đó (kể
  cả một chữ "giữ"); bước để trống thì không ghi gì.
- Rule mới chạy dry-run (Tools ▸ Draft rule, wave 8/9) trên file mẫu trước khi bật, để
  anh thấy nó bắn gì.
- Phiên này không thêm gì vào `principles.yaml`, `automix.yaml`, `feedback.jsonl`: chưa có
  số hay verdict nào của anh.

## Q6 — cảnh nghi vô lý agent đưa ra để anh xác nhận

Nguồn: hợp đồng advisory cố định trên `user-files/example-Vu.snap`
(`tests/test_advisory_realfile.py`, sinh từ lần chạy 2026-08-17; giá trị kênh lấy từ
docstring đã soi raw `ae_data` trong `tests/test_advisory_rules_presets.py`). Đây
**không** phải một lần chạy Doctor mới; 5 file mẫu còn lại trong `user-files/` chưa soi.

| Mã | Rule | Kênh | Tool báo | Vì sao nghi vô lý |
|---|---|---|---|---|
| X1 | PB5 (info) | ch.13 "Kick In", HPF 55.2 Hz | "Kick HPF cao hơn 45 Hz" | Mic kick in lấy attack; sub đã nằm ở ch.14 "Kick Out" (HPF 32.6 Hz, không bị báo) |
| X2 | PB2 (info) | ch.21 "Hihat", HPF 502.4 Hz | "ngoài cửa sổ 160–250 Hz" | HPF hi-hat cao hơn sách để bớt bleed là chuyện thường ở live |
| X3 | PB4 (info) | ch.22 "OH", HPF 120 Hz | "dưới sàn 160 Hz" | Overhead giữ thân trống ở 120 Hz có thể là chủ ý |
| X4 | PB1 (info) | ch.16 "Snare Bot" | "chưa đảo pha" | Input của kênh chưa patch (nguồn `grp OFF`): báo pha trên kênh không có tín hiệu |
| X5 | G9 (warning) | bus.7 "SIDEFILL" | "monitor không bật dynamics" | Sidefill có thể đã có limiter ở loa/processor |

Thêm một câu: G8 (send post-fader sang monitor) đã tắt dưới `--profile small` (ROADMAP §5
mục 4 + `shows/small.yaml`); nó có phải nhiễu cả ở các show khác không? G10 dưới `small`
đã chốt 2026-10-20, không hỏi lại.

Anh trả lời từng mã: *vô lý* / *đúng* / *tùy loại show (loại nào)*, ở bước Q6 của HW-256.
