# Chuẩn bị brainstorm hướng 3: advisory mã hoá gu mix của ToanAZ

Ngày 2026-10-22. Tài liệu CHUẨN BỊ, không phải thiết kế. Chưa quyết gì; wave này chỉ
bắt đầu sau khi ToanAZ trả lời mục 2. Bối cảnh: `docs/ROADMAP.md` §1 ("wrong" = gu mix
của chính ông, mã hoá thành ba lớp YAML), §5 mục 10.3 (hướng 3 chưa scope), và
`docs/proposals/2026-10-21-fable-options.md` §4 B + §6 Q6/Q7 (nằm trên nhánh
`origin/docs/fable-options`; B không cần bàn nhưng 100 % phụ thuộc `source:` /
`rationale:` của owner).

## 1. Hiện trạng (đo ngày 2026-10-22 trên `origin/main`)

**Ba lớp** (`wing_parser/advisory/layers.py`, `models.py`): `base` (ship trong package)
-> `toanaz` (`knowledge/toanaz/principles.yaml`) -> `show`
(`knowledge/toanaz/shows/<name>.yaml`, chọn bằng `--profile <name>`; tên sai thì raise).
Rule có `hardness: hard|flexible` (flexible chỉ chạy khi `applies_when` khớp scene),
`event: universal|corporate|band`, `supersedes: [id]` để tắt rule lớp dưới.

**Base rules: 39 rule, 9 file** trong `wing_parser/advisory/base_rules/`:

| File | Số rule | File | Số rule |
|---|---|---|---|
| `presets_corporate.yaml` | 8 | `showcontext.yaml` | 7 |
| `routing.yaml` | 7 | `presets_band.yaml` | 6 |
| `monitors.yaml` | 3 | `monitors_quality.yaml` | 3 |
| `naming.yaml` | 2 | `speech.yaml` | 2 |
| `dynamics.yaml` | 1 | | |

**Nguồn:** cả 39 `source:` đều trỏ vào `docs/knowledge-base/...` (Core-Skills-Overview,
Technical-Rider-Spec, Live-Entertainment-Shows, Corporate-B2B-Events,
AI-Plugins-In-Live-Sound). KHÔNG rule base nào có `source:` là lời ông. Ông chỉ xuất hiện
trong `rationale:` như quyết định về severity/phạm vi: G8 (câu ông nói về TAP sends), G9
(severity thấp hơn), `presets_corporate.yaml` (ship ở `info`, 2026-08-16), `showcontext.yaml`
(quyết 2026-08-17; Q7 ghi "ToanAZ deferred the threshold" vì chưa có số của rig). Tức là
tool đang là "textbook + vài quyết định về mức độ", chưa phải "gu của ông".

**Lớp của ông gần như rỗng:**
- `knowledge/toanaz/principles.yaml`: `principles: []`.
- `knowledge/toanaz/shows/small.yaml`: 2 rule, `source:` đều là ông
  (`show.small.post-monitors-are-deliberate` supersedes G8;
  `show.small.no-ambient-mic-is-the-rig` supersedes G10, ông xác nhận 2026-10-20).
- `knowledge/toanaz/feedback.jsonl`: 0 dòng (chưa verdict nào được ghi).

**Vòng feedback hôm nay** (`wing_parser/advisory/feedback.py`): log append-only, mỗi dòng
gồm `finding_id` (`<rule>:<target>`), `verdict` in `correct | false-positive | irrelevant`,
`note`, `scene`, `recorded_at`. Ghi bằng `wing feedback <finding_id> --verdict ...`
(`wing_parser/cli/commands.py`) hoặc hai cú bấm ở verdict bar trong Doctor
(`wing_parser/ui/verdict_bar.py`). Docstring nói thẳng: KHÔNG có machine learning; log chỉ
để khi đọc qua nhiều show thì thấy mẫu (vd 7 lần reject G8 trong scene có đúng 1 monitor
bus), rồi NGƯỜI viết principle; Claude chỉ đọc log và đề xuất. Chưa có nút nào biến verdict
thành rule; mọi bước sau verdict là làm tay.

**Giới hạn đã biết:** `$fdr` vs `fdr` (ROADMAP §5.5, ông chốt 2026-10-20: rule về cái khán
giả nghe đọc `$fdr`, về cấu hình strip đọc `fdr`); limiter `dyn.mdl` còn "later" (§5.3,
`docs/handoff/2026-08-17-limiter-token-probe.md`) nên G7 chưa tin được.

## 2. Câu hỏi cho ToanAZ (14 câu; ★ = 5 câu quan trọng nhất)

Mỗi câu trả lời được trong 1-2 câu, tại bàn hoặc qua điện thoại.
**A. Inputs (tool được nhìn gì)**
1. ★ Trong `.snap`, thứ gì ông tin được (gain, fader, HPF/EQ, dyn, sends) và thứ gì ông luôn
   chỉnh LẠI tại show nên giá trị lưu sẵn vô nghĩa (vd gain)?
2. Tool nên soi scene lưu (sau soundcheck), desk live lúc đang chạy, hay cả hai với hai bộ
   rule khác nhau?
3. Loại show/venue/số người: ông chọn profile bằng tay (như `small`) hay muốn tool đọc từ cue
   sheet? Ông thường có mấy loại show (small, corporate, band lớn...)?

**B. Rule of thumb theo loại nguồn**
4. ★ Kick: HPF bao nhiêu (hay off), gate/comp mặc định, và cấu hình nào ông coi là "sai" dù
   sách cho phép? (PB5 hiện theo sách: off hoặc không quá 45 Hz.)
5. ★ Vocal lead / MC: HPF, comp ratio tối đa, có de-ess không, fader range hợp lý. Số của
   ông khác sách chỗ nào? (S1 và PC1..PC8 đang theo sách.)
6. ★ IEM: cái gì ông coi là LỖI chứ không phải sở thích (limiter bắt buộc, ambient, pre/post,
   HPF)? Và danh sách model limiter ông dùng (trả luôn ROADMAP §5.3; mở menu dyn model trên
   WING-Edit, khoảng 5 phút).
7. Snare/hi-hat/ride/overhead (PB1..PB4): ông đồng ý cửa sổ HPF trong sách (hi-hat 160-250,
   ride 200-300, overhead 160-450 Hz) hay có số khác?
8. Playback/click/talkback (R1, R2, S2): nguồn nào ông luôn muốn tool bỏ qua, nguồn nào luôn
   bắt?

**C. Gain staging**
9. ★ Mục tiêu của ông: peak input bao nhiêu dBFS cho vocal, kick, playback; headroom để lại
   trên master là bao nhiêu (dBFS hay LUFS)?
10. Fader "thường trú" nằm ở đâu (vd vocal quanh 0 dB, ±6)? Fader ngoài khoảng đó có nghĩa là
    gain staging sai (lẽ ra kéo gain, không kéo fader) không?

**D. Khi nào rule KHÔNG được bắn**
11. ★ Kể 3 cảnh tool bắn mà ông thấy "ngu": loại show nào, nguồn nào, vì sao. Đó chính là
    `applies_when` hoặc `supersedes` của ông.
12. Rule nào chỉ nên nhắc trước show (soundcheck) và im lặng khi đang show, rule nào ngược lại?
    Cái gì ông muốn là `error`, cái gì chỉ `info`?

**E. Ông muốn dạy tool thế nào**
13. Ông dạy bằng cách nào: (a) form trong wing-ui ("rule mới từ finding này", điền số), (b)
    đọc voice note/transcript rồi agent đề xuất YAML để ông duyệt, hay (c) tự sửa YAML? Ông
    chịu bỏ bao nhiêu phút mỗi show?
14. Khi agent đề xuất principle từ log verdict (vd 7 lần reject cùng điều kiện), ông duyệt từng
    cái trong UI hay một lô cuối tuần? Ông có chịu ghi `note:` một câu mỗi lần bấm verdict
    không (nguồn `rationale:` rẻ nhất)?

## 3. Khung (SKETCH, KHÔNG phải quyết định)

Một principle của ông nằm ở `knowledge/toanaz/principles.yaml` (lớp `toanaz`, thắng base,
áp dụng mọi show; nếu chỉ đúng cho một loại show thì để ở `shows/<name>.yaml`). Dùng đúng
shape đang chạy (xem PB5 trong `wing_parser/advisory/base_rules/presets_band.yaml`). Mọi số
và tên nguồn dưới đây là chỗ giữ chỗ; tên field predicate chỉ lấy từ PB5, chưa kiểm với
scene thật.

```yaml
principles:
  - id: toanaz.kick.hpf-window            # sketch
    title: "Kick high-pass outside my window"
    severity: warning
    hardness: hard                        # hoặc flexible + applies_when
    source: "ToanAZ <date>: <quote>"      # PLACEHOLDER: lời ông, nguyên văn
    rationale: >
      <vì sao, một hai câu, từ chính ông>
    supersedes: [PB5]                     # tắt rule sách; PB5 vẫn nằm ở base
    requires_classifier: true
    when:
      for_each: channel
      where:
        channel.filter.low_cut_on: true
        channel.filter.low_cut_hz: {gt: <X>}      # X do ông cho
        channel.source_type: {starts_with: drums.kick}
    message: >
      Channel {channel.number} ({channel.name}): kick HPF is {channel.filter.low_cut_hz} Hz.
```

Override: `supersedes` tắt rule base cùng chủ đề (như `show.small.*` tắt G8/G10); không
`supersedes` thì rule chạy cạnh base. `source:` = câu ông nói kèm ngày (convention của
`knowledge/toanaz/shows/small.yaml`).

## 4. Agent làm được khi chưa có ông, và không làm được

**Làm được (offline, không cần bàn):**
- Dựng "hộp dạy" phía code: form UI "rule từ finding" ghi vào `principles.yaml` (validate qua
  `layers.py`); báo cáo log verdict theo rule (đã có `read_log`); gợi ý mẫu ("rule X bị reject
  N lần với điều kiện chung Y").
- Validator + test ép rule lớp `toanaz` phải có `source:` dạng `ToanAZ <date>: <quote>` (chống
  rule bịa "của ông" mà không có lời ông).
- Biến transcript voice note thành DRAFT YAML (đánh dấu draft, không tự bật), chạy dry-run
  trên các scene `.snap` mẫu để ông thấy rule sẽ bắn gì trước khi duyệt.
- Doctor prose tiếng Việt (ROADMAP B6) và các phần không phụ thuộc gu.

**Không làm được (chặn ở ông):**
- Mọi con số và `source:` / `rationale:` thật. Không bịa, không suy từ sách rồi gán cho ông
  (ràng buộc "Never fabricate", ROADMAP §2). Câu 4-10 phải do ông trả lời.
- Danh sách limiter `dyn.mdl` (câu 6): không suy ra được offline (3 probe đã thử).
- Biết rule nào ông coi là "ngu": `feedback.jsonl` đang 0 dòng. Cách dạy (câu 13), severity: ông chọn.
- Tự bật principle làm đổi finding của show thật khi ông chưa duyệt.
