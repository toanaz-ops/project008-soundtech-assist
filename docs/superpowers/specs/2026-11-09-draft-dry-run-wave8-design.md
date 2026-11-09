# Wave 8 — Draft-rule dry-run (hướng 3, phần không cần gu) — 2026-11-09

**Vì sao:** mọi rule lớp `toanaz` phải là lời ông (`source:` có `ToanAZ` + ngày ISO,
PR #43) và nội dung gu đang chặn ở HW-191.Q1–Q6. Khi ông (hoặc agent chép từ voice
note của ông) viết một rule **nháp**, ông cần thấy rule đó **sẽ đổi gì** trên các scene
thật trước khi chép nó vào `principles.yaml`. Prep doc
`docs/proposals/2026-10-22-mix-taste-prep.md` §4: "Biến transcript voice note thành
DRAFT YAML (đánh dấu draft, không tự bật), chạy dry-run trên các scene `.snap` mẫu".

## Quyết định (agent tự chốt, ghi lại để ông lật nếu muốn)

- **D1 — Nháp nằm ở đâu:** `<knowledge_dir>/drafts/*.yaml` (cạnh `principles.yaml`,
  không phải trong `shows/`). Cùng schema với `principles.yaml` (khoá `principles:`).
  Vị trí thư mục **là** dấu "draft": resolver/Doctor **không bao giờ** đọc `drafts/`,
  nên một nháp không thể đổi finding của show thật (prep doc §4 "không tự bật").
- **D2 — Kiểm nháp:** cùng mọi luật validate của `layers._as_rules` (schema, severity,
  event, where/any_of, applies_when, supersedes trỏ base id có thật) — lỗi nào cũng
  hiện thành câu, không crash. **Riêng** luật `source:` (ToanAZ + ngày) **không chặn**
  dry-run: nháp chép từ voice note có thể chưa đủ ngày. Thay vào đó báo
  **"Chưa chép sang principles.yaml được"** kèm lý do. Id nháp trùng id principle/base
  có sẵn → lỗi.
  *Cách làm:* `layers._as_rules` nhận thêm `owner_source: bool = True` (mặc định giữ
  y hành vi cũ); `load_draft` gọi với `False` rồi chạy `_validate_owner_source([rule],
  path)` từng rule trong `try` để điền `promote_blockers` — không chép lại logic
  validate. `load_draft` cũng kiểm **lúc load** (một lần, không lặp theo scene):
  `supersedes` phải là id base có thật (`load_base_rules()`), không được trỏ id
  principle; id nháp không trùng id base hay id trong `principles.yaml`.
- **D3 — "Đổi gì" nghĩa là đổi finding, không đổi scene:** với mỗi scene, chạy
  advisory hai lần — **trước** (rule đang có hiệu lực, không profile) và **sau**
  (thêm nháp như rule lớp `toanaz`, tức là `supersedes` / `applies_when` / `hardness`
  có tác dụng y như khi đã chép vào principles). Hiệu = multiset theo
  `(rule_id, target, message)`: **+ mới** (nháp bắn) và **− mất** (rule base bị nháp
  `supersedes` tắt). Không bao giờ ghi gì ra desk, ra scene hay ra `principles.yaml`.
- **D4 — Scene mẫu:** mặc định = scene đang mở bên Doctor (nếu có) + các file gần đây
  (`recent files`) đuôi `.snap` còn tồn tại; ông thêm/bớt file bằng nút. Scene đọc lỗi
  → một dòng lỗi, các scene khác vẫn chạy. Chạy đồng bộ với con trỏ chờ (không
  QThread — tránh rủi ro D-58 trên PySide6 6.12; ≤ vài chục scene là đủ nhanh).
- **D5 — Không profile:** dry-run chạy không `--profile` (principles + base). Profile
  show là chuyện của `shows/`, không phải nháp principle.

## Phạm vi

1. **Hàm thuần (không Qt)** `wing_parser/advisory/draft_dry_run.py`:
   - `list_drafts(directory) -> list[Path]` — `drafts/*.yaml|*.yml`, sắp theo tên.
   - `load_draft(path) -> DraftLoad` — `rules`, `error: str | None`,
     `promotable: bool`, `promote_blockers: list[str]` (lý do theo từng rule).
   - `dry_run(scene, draft_rules, directory) -> SceneDelta` — `before`, `after`
     (số finding), `added`, `removed` (list `Finding`), `suppressed` (map base id →
     draft id). Dùng lại `resolver` (thêm tham số `extra_rules` cho `active_rules`,
     mặc định rỗng → hành vi cũ không đổi một byte).
   - `dry_run_files(paths, draft_rules, directory) -> list[SceneResult]` — load từng
     `.snap`, gom lỗi theo file.
2. **UI:** Tools ▸ **Draft rule dry-run…** (EN) / **Chạy thử rule nháp…** (VI) mở
   dialog: chọn nháp (combo các file trong `drafts/` + nút Browse…), trạng thái nháp
   (lỗi / số rule / promotable hay lý do chưa), danh sách scene (Add… / Remove), nút
   **Run**. Kết quả: bảng tóm tắt theo scene (Scene, Before, After, +New, −Gone, lỗi) và
   bảng chi tiết (Scene, +/−, Rule, Target, Message); chọn một scene thì lọc bảng chi
   tiết. Không có nháp nào → một câu chỉ chỗ đặt file (`<knowledge_dir>/drafts/`) và
   nút mở thư mục. Mọi chuỗi qua `texts*.py` (EN + VI), số dùng font mono.
   File UI ≤ 200 dòng mỗi file.
3. **Không** có nút chép nháp sang `principles.yaml`, không gọi model, không đụng bàn.

## Không làm (wave sau nếu ông muốn)

- Nút "Promote" chép nháp `promotable=True` sang `principles.yaml` (có `.bak`, như
  Fix của lint) — **wave 9, agent làm được**; ông là người bấm nút.
- Sinh nháp từ voice note bằng AI.
- Dry-run có profile show.

## Kiểm

TDD cho hàm thuần: nháp bắn thêm finding (+), nháp `supersedes` base (−), nháp
`hardness: flexible` + `applies_when` không khớp → không đổi gì, `source:` thiếu ngày →
vẫn chạy nhưng `promotable=False`, id trùng → lỗi, YAML hỏng → lỗi, `active_rules`
không có `extra_rules` cho kết quả y hệt trước, resolver không bao giờ đọc `drafts/`.
Một test chạy thật trên `user-files/example-Vu.snap`. Test UI: dialog mở, không nháp →
câu hướng dẫn; có nháp + scene → bảng tóm tắt đúng số; lọc theo scene; scene lỗi hiện
dòng lỗi. Parity EN/VI qua test parity có sẵn.
