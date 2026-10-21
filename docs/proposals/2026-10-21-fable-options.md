<!-- Fable strategic review 2026-10-21, model claude-fable-5-1 (read-only), dispatched by DEV MASTER on owner request. -->

# PROJECT008 — Fable review & phương án (2026-10-21)

Model: claude-fable-5-1 (read-only). **Không có shell trong agent này** → `gh pr list` và `git log origin/main` KHÔNG chạy được; trạng thái PR lấy từ handoff + cross-review + `.git/FETCH_HEAD`, ref origin đọc từ `.git/logs/refs/remotes/origin/main`. Mọi số liệu khác trích từ file trong repo.

## 1. Hiện trạng đo được

**Ref.** Local `main` = `17b8867` (`.git/refs/heads/main`); `origin/main` đã fetch tới `f6757dc` sau 4 lần fast-forward kể từ `17b8867` (`.git/logs/refs/remotes/origin/main:21-25`) → checkout local lại tụt sau origin, đúng cảnh báo audit (`shared/audits/p008-fable-audit-20261021.md:115-119`). Các nhánh fix từ audit đang tồn tại trên origin: `fix/write-readback-ledger`, `fix/net-datagram-resilience`, `fix/authorize-skip-identity`, `fix/revert-dialog-esc`, `fix/write-ui-small`, `fix/writelog-followups`, `docs/audit-drift`, `fix/worker-shutdown-612` (`.git/FETCH_HEAD:3,13,16,19,23-26`). Handoff xác nhận #22, #23 (wave 5), #26/#32/#33 đã merge (thêm #34, ghi bước 3 của D-58, cũng đã merge; `origin/main` = `f6757dc`); #24, #25, #27–#31 do phiên khác mở, vẫn OPEN (`shared/handoff/handoff-20261021-p008-wave5-write-log.md:14-27,43-44`). Cross-review không có HIGH, thứ tự merge #29→#31→#27→#28→#25→#30→#24, #24 đang được sửa thứ tự `ledger.add → _badge → apply_result` (`shared/audits/p008-audit-prs-cross-review-20261021.md:5-16`).

**Waves đã xong (merged, CI `test` xanh):** Phase 1, A, B, G1, H, C·D, C2, G2a, G2b, GUI 1/1b, GUI 2 (Console read-only), GUI 3 (ghi 1 lá OSC/lần từ Doctor), GUI 4 (import + vocabulary), Bilingual, GUI 5 (write log + report HTML, trang Log Ctrl+8) — `docs/ROADMAP.md:80-94`, `:315-379`; suite cuối `DAT 2293 / 0 fail / 3 skip` (handoff `:26`). Exe phát hành từ `17b8867` trên PySide6 6.11.2, `dist\wing-ui-20261021.zip` (handoff `:27`).

**Đã chứng minh trên bàn thật (WING-GIAQUY, wing-rack FW 3.1, 192.168.128.28):**
- Lớp `net/` CLI: đọc toàn bàn 25 170 lá / 3.2 s, push 21 344 lá, advisory live = file (22/22), clamp im lặng `fdr=999 → +10 dB`, ghi dạng string hiển thị (1919 → 5 lá sai) — `docs/handoff/2026-08-21-wing-net-complete.md:57-69`, `docs/superpowers/specs/2026-08-21-wing-net-design.md:226-258`.
- Live watch 120 s, ~150 sự kiện, phát hiện trong ~250 ms, WING-Edit cùng chạy không bị đá — `docs/ROADMAP.md:381-400`.

**Chỉ chứng minh bằng FakeWing/FakeDesk (chưa hề chạm bàn thật qua UI):**
- Toàn bộ đường ghi từ UI (Arm, 3 mức apply, countdown, read-back badge, Revert/Revert all): runbook tự ghi "Nothing below has touched a real console before this session" — `docs/acceptance/2026-09-wave3-desk-acceptance.md:13-14`; ROADMAP §5.9.4 "still not run" (`:305-310`).
- Trang Console wave 2 §9.3 + 15 ruling ASSUMED — `docs/ROADMAP.md:256-269`.
- Wave 4 import với key thật và cue sheet thật qua exe — `docs/ROADMAP.md:327-331`.
- Wave 5 Log/Export (bước 6b) — handoff `:38-40`; `live_write.REAL._read` không có unit test (D-52 #3, `docs/tech-debt.md:888-889`).
- Settings ▸ Test connection từ exe đóng gói — `docs/ROADMAP.md:302-304`.
- Tên kênh tiếng Việt qua OSC: chưa đo, hai `.snap` mẫu không có non-ASCII (audit `:25`).

Gate "no surface is done until ToanAZ has looked at the screenshots" (`docs/ROADMAP.md:328-329`) chưa đóng cho wave 2, 3, 4, bilingual, 5.

## 2. Mục tiêu repo tự nói vs thực tế

- **Mục tiêu:** đọc `.snap`/bàn thật, phân loại, cảnh báo cấu hình sai theo gu mix của ToanAZ; UI-first ("không ai chạy script tại venue") — `CLAUDE.md:9-15`, `memory/MEMORY.md` mục 2026-08-24; ghi vào bàn thật chỉ sau khi hỏi, không bao giờ trong show — `CLAUDE.md:17-22`.
- **Ràng buộc nền:** "Evidence, not assertion — a measurement nobody can re-run is not evidence" — `docs/ROADMAP.md:66`.
- **Độ lệch 1 (lớn nhất):** 4 wave UI liên tiếp (2→5) xây chồng lên đường ghi mà chưa có bằng chứng nào trên bàn thật; wave 5 còn thêm "sổ ghi làm bằng chứng sau show" lên đường chưa nghiệm thu. Chính ràng buộc §2 bị vi phạm ở lớp nguy hiểm nhất.
- **Độ lệch 2:** ROADMAP tự nhận là "single source of truth" (`:20-23`) nhưng bảng Done dừng ở GUI 3 (`:94`); wave 4/bilingual/5 chỉ nằm ở §5 "open" dù đã merge (audit `:97`). README còn "seven pages / Ctrl+1…7" (`README.md:50,80`) trong khi đã 8 trang.
- **Độ lệch 3:** hướng "advisory mã hoá gu mix" (lý do tồn tại của tool, `docs/ROADMAP.md:37-40`) chưa có wave nào từ B (2026-08-17); §5.3 limiter list vẫn "later" (`:234-239`).

## 3. Rủi ro lớn nhất (chi tiết ở audit)

1. **Bàn ĐÃ đổi nhưng app báo "refused" → sổ/log thiếu dòng, không Revert được.** `_set_leaf` bắn datagram rồi mới read-back; mọi exception sau đó (ConnectionResetError, ValueError codec, CallTimedOut 10 s) rơi vào `on_failure` — `wing_parser/net/write.py:117-123`; audit `:16-21`. Fix trong PR #24 (đang sửa thứ tự). Đây là rủi ro trực tiếp nhất với mục tiêu wave 5.
2. **Cổng "không trong show" là tự khai.** Chốt an toàn duy nhất chống ghi lúc show là ô tick "This desk is NOT running a show right now" + gõ tên bàn — `wing_parser/ui/texts_write.py:27-33`; không có kiểm tra kỹ thuật nào. Cộng thêm Immediate vẫn ghi mù khi pre-flight read lỗi (`desk_before=None`, không revert được) — D-52 #9 (`docs/tech-debt.md:922-928`), audit `:56-60`, chờ owner quyết.
3. **Một datagram hỏng/non-ASCII làm đổ cả Pull/Discover/Watch** — `net/client.py:243-250`, `codec.py` decode ASCII cứng; show của ToanAZ là tiếng Việt, `read_labels` đọc tên mọi strip lúc bắt đầu Watch — audit `:23-28`. Fix PR #27; nhưng **encoding thực của WING chưa đo**.
4. **Esc/X trên countdown trong Revert all treo cả run**, Doctor bị khoá tới khi bấm Stop — `write_delay_dialog.py:172-179`; audit `:9-14`. Fix PR #25. Mỗi ghi UI tốn 4 round-trip UDP (2 handshake `WING?` thừa) → Wi-Fi venue dễ sinh "refused" giả — `write.py:93-100,117`, audit `:30-35`, PR #28.
5. **Rủi ro quy trình:** CI cài PySide6 mới nhất (`.github/workflows/ci.yml:56`, `pyproject.toml:20` `>=6.11`) trong khi exe build 6.11.2; 6.12 đã abort tiến trình 3 kiểu (handoff `:30-34`; `docs/tech-debt.md:741-755`). Bản phát hành có thể xanh CI trên Qt khác bản ship.

## 4. Phương án wave tiếp theo

**A — Wave 6 = "Hardening + nghiệm thu bàn thật", KHÔNG tính năng mới.** Merge #24–#31 theo thứ tự cross-review, rebuild exe, agent bổ sung test/probe còn thiếu (audit `:101-107`), rồi ToanAZ chạy runbook wave 3 + 6b + wave 4 trong một buổi. Được: đóng gate đã treo 5 tuần, biến 4 wave "built" thành "proven"; mọi fix đều S, agent làm ngay. Mất: 1–2 tuần không có feature; cần ~2 h bàn rảnh + WING-Edit. Công sức **S (agent) + S (owner)**. Không có gì không đảo ngược. Phụ thuộc bàn: **có**.

**B — Hướng 3: advisory mã hoá gu mix của ToanAZ** (`docs/ROADMAP.md:338-339`). Được: đúng lý do tồn tại của tool; không chạm đường ghi, không cần bàn; test offline hoàn toàn. Mất: 100 % phụ thuộc owner cung cấp `source:`/`rationale:` từng rule + limiter list (§5.3); nếu owner bận thì wave đứng. Công sức **M** (rules + Doctor prose VI B6). Không đảo ngược: không. Phụ thuộc bàn: không.

**C — E: transport metering UDP** (`docs/ROADMAP.md:196-202`). Được: mở LUFS/SPL. Mất: cần bàn thật nhiều ngày để probe kênh native; protocol chưa biết; **L**; dễ phình. Phụ thuộc bàn: nặng. Không nên lúc này.

**D — W11: tra show code → tên/venue từ PRJ012 online** (spec wave 5 `:39`). Được: tiện Arm. Mất: cần agent token, laptop thường offline ở venue; thêm bề mặt mạng vào app "offline first". **S–M**. Phụ thuộc owner cấp token. Giá trị thấp so với rủi ro.

**KHUYẾN NGHỊ: A, rồi B.** Lý do: (1) rủi ro 1–4 đều nằm trên đường ghi mà chưa dòng nào chạy trên bàn thật — thêm feature lên đó là chồng nợ bằng chứng; (2) A rẻ (mọi fix đã có PR), phần agent chạy song song trong lúc chờ bàn; (3) B không cần bàn nên có thể brainstorm với owner ngay trong lúc chờ, và sau khi A ký thì B là wave content đầu tiên sau 2 tháng. C và D hoãn.

## 5. Kế hoạch 2 tuần

**Tuần 1 — agent làm ngay (không cần bàn):**
- Merge #29→#31→#27→#28→#25→#30→#24 (sau khi #24 rebase xong), `git pull --ff-only` local main (xin phép theo rule 5).
- Docs sync một PR: ROADMAP §3 thêm hàng GUI 4 / Bilingual / GUI 5, header "Last updated"; README 8 trang + Ctrl+8; 3 comment stale (`menus.py`, `live_controller.py`, `live_wiring.py`); D-40 double status (audit `:91-99`).
- Test gaps audit `:101-107`: read-back-raises qua FakeWing, packet-count `_authorize`, badge sống qua `set_changes`, `reject()` trong Revert all, mixed-offset ordering.
- Probe read-only mới `docs/probes/probe13_nonascii_names.py` (đọc `/ch/N/name`, in bytes thô) để owner chạy 1 phút tại bàn → quyết encoding `.snap` (audit `:85-89`).
- CI: ghim PySide6 = bản exe ship (6.11.2) cho check `test`, thêm job `qt-latest` scheduled được phép đỏ (chờ owner chốt — câu 4).
- Rebuild exe + zip + "gói nghiệm thu": exe, runbook, checklist tiếng Việt 1 trang, lệnh `wing net identity 192.168.128.28` làm baseline P3.

**Tuần 2 — chờ owner tại bàn (1 buổi ~2 h, bàn KHÔNG trong show, WING-Edit mở):**
- Runbook `docs/acceptance/2026-09-wave3-desk-acceptance.md` bước 1–9 + 6b; runbook wave 4 với key DeepSeek thật; probe13; xem screenshot `dist-shots\exe-20261021-*`.
- Agent trực cùng ngày sửa bước đỏ; sau khi ký: đóng ROADMAP §5.8/5.9/5.10/5.12, D-52 #3, ghi handoff.
- Nếu bàn không rảnh trong 2 tuần: agent chuyển sang chuẩn bị B (danh sách câu hỏi gu mix cho owner, khung rule YAML, không merge gì lên đường ghi).

## 6. Câu hỏi owner cần chốt

1. **Khi nào WING-GIAQUY rảnh ~2 h cho nghiệm thu?** Khuyến nghị: trước mọi feature mới; đây là nút thắt duy nhất của wave 6.
2. **Immediate khi pre-flight read lỗi: từ chối (như Delayed) hay giữ + badge riêng?** (D-52 #9) Khuyến nghị: **từ chối** — `desk_before=None` phá cả Revert lẫn log; nhất quán 3 mức.
3. **Ô "NOT running a show" giữ nguyên tự khai, hay thêm cảnh báo mềm khi Watch thấy fader/mute đang chuyển động trong 30 s gần nhất?** Khuyến nghị: thêm **cảnh báo mềm, không chặn cứng** (soundcheck cũng có chuyển động; chặn cứng sẽ gây bỏ qua ô tick).
4. **PySide6 trong CI: ghim theo bản exe ship hay thả nổi?** Khuyến nghị: **ghim** cho check `test` + job `latest` được phép đỏ; đỏ do Qt mới không phải lý do chặn merge.
5. **Encoding `.snap` cho tên tiếng Việt** (hai writer đang khác nhau, audit `:85-89`): cần một file do WING-Edit lưu với tên có dấu. Khuyến nghị: owner lưu 1 scene "Ca sĩ Đức" từ WING-Edit bỏ vào `tests/data/` trong buổi nghiệm thu, agent thống nhất `dump_snap()` theo đó.
6. **Wave content sau khi ký: hướng 3 (gu mix) / E (metering) / W11 (PRJ012)?** Khuyến nghị: **hướng 3**; E vẫn blocked; W11 chỉ khi có thiết kế cache offline.
7. **Limiter model list (§5.3):** 5 phút mở menu dyn model trên WING-Edit lúc ở bàn là đủ. Khuyến nghị: làm luôn trong buổi nghiệm thu để G7 hết "later".

**Đã xác minh khi chép vào repo (2026-10-21, `gh pr list`, bởi phiên ASSIST+):** `origin/main` = `f6757dc`. Đã merge: #19–#23, #26, #32, #33, #34. Còn OPEN: #24, #25, #27, #28, #29, #30, #31. Bốn commit trên origin sau `17b8867` là các merge #26, #32, #33, #34 (docs wave 5 + D-58; #32 là bản sửa production cho lỗi QThread trên PySide6 6.12). Exe phát hành vẫn là bản build từ `17b8867` trên 6.11.2; một exe thử trên 6.12 từ `0378dca` chạy được, nhưng chưa thử thoát app khi lệnh gọi model đang treo (D-58).
