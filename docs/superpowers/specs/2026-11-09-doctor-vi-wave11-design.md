# Wave 11 — Doctor findings in Vietnamese (B6) — 2026-11-09

**Vì sao:** UI song ngữ (2026-09-29) cố ý để phần chữ do lớp phân tích sinh ra
(finding Doctor) bằng tiếng Anh — ruling **B6** trong
`docs/superpowers/specs/2026-09-29-ui-bilingual-design.md`, ghi "Its own wave" /
"candidate next wave". Đây là quyết định phạm vi của agent, không phải lời ông, nên
agent làm được. Ông chạy UI tiếng Việt thì bảng Doctor vẫn toàn tiếng Anh.

## Quyết định (agent tự chốt)

- **V1 — Phạm vi:** chỉ **câu finding** (`message`) và **tiêu đề rule** (`title`) của
  các rule lớp `base`. `rationale`, `source`, repair prose, classifier reason, CLI giữ
  tiếng Anh (CLI không đổi một byte).
- **V2 — Dữ liệu:** rule YAML có thêm khoá tuỳ chọn `message_vi` / `title_vi`.
  `Rule` thêm `message_vi: str = ""`, `title_vi: str = ""`; `Finding` thêm
  `message_vi: str = ""` (render cùng context với `message`). Lớp `toanaz`/`show`
  cũng đọc được hai khoá này nhưng không bắt buộc.
- **V3 — Hiển thị:** khi `current_language() == "vi"` và có bản VI → bảng Doctor,
  detail panel dùng bản VI; thiếu thì rơi về English (như B4). Lọc/sắp xếp/khoá
  feedback dùng `rule_id`, không đổi. Dry-run (wave 8) so khớp theo `message`
  English — không đổi.
- **V4 — Từ ngữ:** danh từ mixer giữ English như trên desk (B2: Bus, Main, Fader,
  Mute, Scene, Gate, Dyn, HPF, Send…). Placeholder `{...}` y hệt bản English.
  Câu VI do agent dịch — **ông duyệt lại** cùng loạt VI đang chờ (không chặn merge).

## Kiểm

- Test parity: mọi rule trong `base_rules/*.yaml` có `message_vi` và `title_vi`
  không rỗng (rule supersede-only không có `message` thì chỉ cần `title_vi`), và tập
  placeholder `{...}` của `message_vi` = của `message`.
- Evaluator: finding có `message_vi` render đúng; rule không có `message_vi` →
  `Finding.message_vi == ""`.
- UI: ở `vi`, bảng findings + detail panel hiện câu VI; ở `en` hiện English; rule
  thiếu VI → English. CLI output không đổi (test snapshot một lệnh doctor/analyze
  có sẵn nếu có).
- Font: ký tự VI đã được font vendored phủ (test glyph có sẵn).
