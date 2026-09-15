# Project memory — PROJECT008-SOUNDTECH-ASSIST (wing-parser)

Index of durable knowledge. Newest at the bottom. Read before designing anything.

---

## 2026-08-24 — PITFALL: venv phải cài đủ extras trước khi build exe

`wing-ui.exe` build xong vẫn chết im lặng (exit 1, console=False nên không in
lỗi) nếu venv thiếu optional extra. Venv mới = phải cài:
`pip install -e ".[ui]"` (PySide6) — và nhớ `[ingest]`, `[llm-openai]`.
Dấu hiệu nhận biết: test UI bị skip trong pytest. Debug exe có terminal:
`packaging/wing-ui-debug.spec` (console=True) → `dist\wing-ui-debug.exe`.
Quy trình build bản phát hành: cài đủ extras → `pyinstaller packaging/wing-ui.spec --noconfirm`
→ Start-Process dist\wing-ui.exe, sleep 6s, kiểm tra process còn sống.

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
   cùng.)**

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
