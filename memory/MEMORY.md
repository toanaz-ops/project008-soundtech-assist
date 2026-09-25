# Project memory — PROJECT008-SOUNDTECH-ASSIST (wing-parser)

Index of durable knowledge. Newest at the bottom. Read before designing anything.

---

## 2026-08-24 — PITFALL: venv phải cài đủ extras trước khi build exe

`wing-ui.exe` build xong vẫn chết im lặng (exit 1, console=False nên không in
lỗi) nếu venv thiếu optional extra. Venv mới = phải cài:
`pip install -e ".[ui,ingest,llm,llm-openai]"`. Dấu hiệu nhận biết: test UI
bị skip trong pytest. Debug exe có terminal: `packaging/wing-ui-debug.spec`
(console=True) → `dist\wing-ui-debug.exe`. Quy trình build bản phát hành:
cài đủ extras → `pyinstaller packaging/wing-ui.spec --noconfirm` →
Start-Process dist\wing-ui.exe, sleep 6s, kiểm tra process còn sống.
**(Cập nhật 2026-09-25, C1 quyết bởi ToanAZ):** bản phát hành PHẢI có cả hai
SDK model, `anthropic` (extra `llm`) và `openai` (extra `llm-openai`), để
Settings ▸ Test connection và AI assist trong Import chạy được từ exe — vì
vậy dòng cài giờ là `.[ui,ingest,llm,llm-openai]`, không phải chỉ `.[ui]` +
`[ingest]` + `[llm-openai]` như trước (thiếu `llm`/anthropic). `mcp` vẫn cố ý
KHÔNG cài — `packaging/wing-ui.spec`'s `EXCLUDES` cũng loại nó ra khỏi bundle.
Exe phát hành hiện tại (tính đến 2026-09-25) CHƯA được build lại với các
extra này.

## 2026-08-24 — UI-FIRST LÀ RÀNG BUỘC SỐ 1

**Nguồn:** ToanAZ, nói trực tiếp 2026-08-24.

> Đi show xài giao diện UI bấm chuột, **không ai chạy script tại venue**.

Hệ quả thiết kế — áp dụng cho MỌI tính năng mới:

1. Tính năng chỉ được coi là "xong" khi có nút bấm trong `wing-ui` desktop app.
   CLI/script-only = chưa tồn tại với người dùng.
2. Script tạm, probe đo đạc, công cụ thử nghiệm → để trong **dev mode**
   (menu ẩn/khu dev trong UI), không trộn với luồng show.
3. Thứ tự ưu tiên chu kỳ UI: **import cue sheet lên UI trước** (việc hàng tuần
   khi đi show), rồi doctor/analyze đầy đủ, rồi console live panel.
4. Hiện trạng mốc này (2026-08-24): desktop app chỉ phủ luồng doctor
   (findings/repairs/verdicts). Import, analyze/channel/routing, diff,
   toàn bộ `net` — vẫn CLI. **(Cập nhật 2026-09-16: câu này đã SAI —
   2026-08-26 wave 1 đưa import/analyze/channel/routing/diff lên UI;
   2026-09-16 wave 2 đưa phần ĐỌC của `net` lên UI (trang Console).
   Chỉ còn `net set/toggle/push/get` là CLI-only, cố ý — xem mục dưới
   cùng.) (Cập nhật 2026-09-18: wave 3 đưa phần GHI lên UI — nhưng KHÔNG
   phải bốn lệnh đó. Đường ghi duy nhất là nút Repair bên Doctor, một lá
   OSC mỗi lần; `net set/toggle/push/get` vẫn CLI-only, vẫn cố ý.)**

## 2026-08-24 — G2b merged

Provider layer (Anthropic + OpenAI-compatible/DeepSeek), assisted ingest model
half, wizard + `--one-shot`, structured sound/lighting/led fields. Chi tiết:
`docs/handoff/2026-08-24-g2b-assisted-ingest-complete.md`. Suite 1274 passed /
21 skipped @ `6324fa6`. Còn treo: live DeepSeek smoke (cần key), seed từ vựng
cuesheet (§5.2 ROADMAP).

## 2026-08-26 — SAO KẾT THÚC PHIÊN: re-read file trước edit đầu tiên sau gián đoạn

Task 1b-18: sau khi phiên bị ngắt (mạng/quota), working tree KHÔNG còn khớp lần
đọc cuối — task song song đã commit cả edit đang dở của phiên này (282ba11).
Edit tiếp từ stale read làm TRÙNG dòng `set_style`; chỉ nhờ phiên song song ghi
đè lại mà sạch. Luật: sau MỌI gián đoạn, `git status` + `git log` + re-read file
TRƯỚC khi edit. Chi tiết: `.superpowers/sdd/2026-08-25-gui-parity-wave1/task-1b18-report.md` §6.

## 2026-08-26 — GUI parity wave 1 + house style 1b HOÀN TẤT

Sáu trang trong wing-ui: Doctor/Overview/Channels/Routing/Diff/Import
(G2a+G2b wizard, AI assist qua Settings — người dùng tự dán key riêng).
Dark Sodium Rack: 19 token int sinh QSS bằng Template.substitute, test cấm
hex ngoài theme/, font OFL vendored (weight chọn bằng QFontInfo), mono cho
mọi số, cắt chữ giữa-giữ-đuôi. Model call: worker + Cancel + timeout
(120/180/30s). Phím tắt Ctrl+O/Shift+S/Z/Ctrl+1..6/F5/Esc; nhớ geometry/
trang/file gần đây. Exe: `dist\wing-ui.exe` (onefile) — screenshot từng
trang từ exe đều đạt; debug spec là sinh phẩm của make-debug-spec.py.
Suite **1433 passed / 3 skipped** @ `04db887` (branch
feature/gui-parity-wave1, CHƯA merge — chờ ToanAZ). Cửa chặn done: không
trang nào xong nếu ToanAZ chưa nhìn ảnh từ exe. Còn mở: D-24 scanner test,
D-29 import_page 246 dòng, D-30 placeholder-key, D-31 settings.cancel key,
live DeepSeek smoke trong app. Nợ: docs/tech-debt.md.

## 2026-09-15 — Chuyển sang quy trình GitHub-oriented

Repo GitHub `toanaz-ops/project008-soundtech-assist` tạo 2026-08-23 nhưng mãi
2026-09-15 mới nhận push đầu tiên: ba tuần toàn bộ công việc nằm trong `main`
local (337 commit, 149 theo first-parent), không ai nhìn thấy, không CI, không
chỗ review. Từ nay: nhánh → push → PR → CI xanh (check tên `test`,
`.github/workflows/ci.yml`, windows-latest + Python 3.12) → ToanAZ merge trên
GitHub → `git pull --ff-only`. Luật và lệnh: `docs/git-workflow.md`.
Extra `mcp` cố ý KHÔNG cài trong CI — suite có test chỉ chạy khi `mcp` vắng.

## 2026-09-16 — GUI wave 2: trang Console (read-only) trên nhánh, chờ merge

Trang thứ 7 trong wing-ui: Connect (`net identity`), Discover (dò schema),
Pull (`net snapshot`) + Export .snap + Open Doctor, Start watch
(`net watch`) — bảng sự kiện sống. Không nút ghi nào (`set/toggle/push/get`
vẫn CLI-only, cố ý). Suite **1573 passed / 3 skipped** @ `e8e3de1`, nhánh
`feat/gui-live-console-wave2`, PR #4 stacked trên PR #1 — **CHƯA merge**.
Còn treo: nghiệm thu §9.3 trên console thật (WING-GIAQUY, ToanAZ chưa nhìn
ảnh từ exe); 3 câu hỏi mở (alert cho watch? có wave 3 ghi không?
auto-connect lúc khởi động?); loạt ruling ASSUMED chờ ToanAZ duyệt lại —
xem ROADMAP §5 mục 8 và `docs/handoff/2026-09-16-gui-live-console-wave2-complete.md`.
**(Cập nhật 2026-09-17: đã merge `dcf897a` — PR #1–#4 (`bedad80`, `00949c4`,
`56d5114`, `dcf897a`) tất cả đã merge vào `main` qua GitHub, CI xanh
1580 passed / 3 skipped. Nghiệm thu §9.3 trên console thật và 15 ruling
ASSUMED vẫn còn treo, chờ ToanAZ.)**

## 2026-09-18 — GUI wave 3: UI ghi được ra console thật, trên nhánh, chờ merge

Nút **Repair** bên Doctor giờ gửi được ra desk — **một lá OSC mỗi lần**,
không `push`, không gộp. Ba mức **Manual / Delayed / Immediate** sau một
bước **Arm** một lần cho mỗi kết nối (hỏi lại identity tươi, tick ô "desk
KHÔNG chạy show", gõ đúng tên desk); đồng hồ đếm ngược có **Apply now /
+5 s / Cancel**, **hết giờ là gửi**; đọc lại xong ra **ba** huy hiệu ✓ / ⚠
/ ✗ và mỗi cái đổi scene một kiểu khác nhau; sổ **Sent to console** có
Revert từng dòng và **Revert all** đi ngược thứ tự, tuần tự, có Stop.
Năm cổng chặn, trong đó `live_write.send` hỏi lại serial ngay trước khi
gửi (`DeskChanged`). Test `test_ui_live_is_read_only.py` **không còn cấm
tiệt** — nó thành **allow-list đúng một module**, `ui/live_write.py`; luật
cấm verb (`toggle`/`push`/`node_write`) vẫn chạy trên cả file được
allow-list. Suite **1761 passed / 3 skipped** @ `f56813c` (đọc bằng
`--junitxml`, xem D-47), nhánh `feat/gui-write-wave3`, **CHƯA merge, chưa
có PR**. Exe đã build lại và còn sống; ảnh chụp đủ bảy trang + tám bề mặt
ghi, **ToanAZ chưa nhìn** — cửa chặn của wave 1.

Còn treo: nghiệm thu §9.3 trên console thật (WING-GIAQUY, chưa chạy dòng
nào); **3 câu hỏi mở** (Immediate lúc đang WATCHING? một đồng hồ chung cho
cả lô Revert-all? arm có sống qua reconnect cùng serial?); **15 ruling W
ASSUMED** chờ ToanAZ lật; và **C1**: venv build cố ý KHÔNG cài
`anthropic`/`openai`, nên nút Test connection trong Settings chưa thử
được từ exe — chờ ToanAZ quyết. Nợ mới D-48..D-53 (trong đó **D-51**: font
vendored thiếu glyph ✗ nên huy hiệu "desk không trả lời" hiện ra ô vuông).
Chi tiết: `docs/handoff/2026-09-18-gui-write-wave3-complete.md`.

**Bẫy đã dính và phải nhớ:** editable install trong `.venv` trỏ về
**checkout chính**, không trỏ vào worktree — build exe từ worktree mà
không `pip install -e` lại thì đóng gói nhầm code cũ, im lặng. Kiểm bằng
`build/wing-ui/Analysis-00.toc`.

## 2026-09-25 — GUI wave 3: ToanAZ đã trả lời cả 19 quyết định treo

Cả 19 mục treo từ wave 3 (3 câu hỏi thiết kế §11, 15 ruling W, C1) đều được
ToanAZ trả lời trong chat, hầu hết giữ nguyên mặc định — spec §5/§11 và
handoff §6 đã cập nhật "FIXED (ToanAZ 2026-09-25)". **C1**: exe phát hành
PHẢI có cả hai SDK model (`anthropic` qua extra `llm`, `openai` qua extra
`llm-openai`) để Settings ▸ Test connection và Import AI assist chạy được
từ exe — dòng cài giờ là `.[ui,ingest,llm,llm-openai]` (`mcp` vẫn cố ý loại
trừ); exe phát hành **đã build lại** từ `main` (`3c2cda9`) ngày 2026-09-25
với các extra này (71.034.002 bytes, còn sống sau 8s) — gap còn lại: nút
Test connection trong Settings chưa thử qua bản exe đóng gói (SDK import
lazy trong `provider.py`), chờ ToanAZ dùng key thật. **Wave 4** (chưa scope,
chờ brainstorm): (a) sổ ghi bền qua nhiều phiên + xuất báo cáo sau show (sẽ
lật ngược W8), (b) import cue sheet tốt hơn (seed từ vựng §5.2, live
DeepSeek smoke trong app), (c) advisory mã hoá gu mix riêng của ToanAZ.
Nghiệm thu §9.3 trên console thật **vẫn chưa chạy** — runbook mới:
`docs/acceptance/2026-09-wave3-desk-acceptance.md`.

Nhánh `fix/wave3-debt-cleanup` (nay **đã merge vào `main` qua PR #9**,
`3c2cda9`, CI `test` xanh) đóng nợ: **D-54** (dist-reports/ vào .gitignore),
**D-50** (tách `write_delay_dialog.py` lấy lại headroom thật, 200→179 dòng),
**D-41** (Console page dùng chung một lần walk schema giữa Discover/Pull
qua `SchemaCache` mới) đã đóng đầy đủ; D-52 mục 1/2/5/8 đóng (thông báo lỗi
dùng `{ROOT}`, `RevertQueue` dùng deque, nhánh chết ở `WriteGate._start`
thay bằng `RuntimeError`, `+5s` tại 0 giây tiếp tục đếm thay vì đứng im).
Một vòng review mới trong PR #9 bắt được D-41 v1 sai (C1: schema chưa đi
hết mà vẫn cache; I1: `SchemaCache.set()` chạy trên worker thread; I2:
`FakeDesk` bỏ qua `schema=`; M1: `+5s` sau pre-flight fail) — đã sửa hết
(`5aabe0e`, `c331b20`). Suite cuối tại lúc merge: **1790 passed / 3 skipped**.

## 2026-09-25 — Luật CI: làm theo PROJECT004

ToanAZ: "nếu CI gặp lỗi hãy dùng cách của PROJECT004". Quy tắc từ
`docs/git-github-oriented.md` §CI của P004: (1) lỗi do MÔI TRƯỜNG CI (suite
cần secret / file gitignore / optional extra không cài trong CI) → skip RÕ
RÀNG, không skip âm thầm — mỗi suite bị skip in một dòng dạng
`SKIP (ci): <name> — <lý do>` và liệt kê trong một registry có tên; (2) lỗi
THẬT → sửa trên cùng nhánh, không được skip. P008 đã cố ý không cài `mcp`
trong CI từ trước và có suite chỉ chạy khi `mcp` vắng mặt — luật mới không
đổi điều đó.
