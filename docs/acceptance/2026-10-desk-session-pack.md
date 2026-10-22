# Gói nghiệm thu tại bàn (WING-GIAQUY, 192.168.128.28) — in 1 tờ A4

**Ngày:** ________ · **Chi tiết từng bước:** [wave 3](2026-09-wave3-desk-acceptance.md) · [wave 4](2026-09-wave4-import-acceptance.md) · Bàn **KHÔNG** trong show, **WING-Edit mở và nối suốt buổi** (rớt thì nối lại, làm lại bước đó).

## 1. Trước khi đi
☐ Exe: `dist\wing-ui-20261021.zip` (PySide6 6.11.2), giải nén, mở thử, đợi ~6 s xem còn chạy ☐ Laptop + cáp mạng/Wi-Fi cùng LAN với bàn ☐ DeepSeek API key ☐ 1 cue sheet `.xlsx` thật + 1 file show-context `.yaml` ☐ Bản in này + bút + điện thoại chụp ảnh ☐ Hỏi venue: bàn đang rảnh, không show.

## 2. Baseline (P3) — chạy TRƯỚC khi mở app
```bash
wing net identity 192.168.128.28
```
Ra 4 dòng: `<tên>  (<model>)`, `serial`, `firmware`, `ip`. Ghi lại: tên ______ serial ______ firmware ______ (mọi bước "identity khớp" so với dòng này).

## 3. Checklist (số bước = trong runbook đầy đủ)
**Wave 3:** ☐ 1 Connect + Pull (Doctor ở Manual) ☐ 2 Arm (Show code, gõ đúng tên, latch) ☐ 3 Manual: Cancel, +5 s ☐ 4 Delayed: hết giờ, Apply now, Immediate ☐ 5a Bool True/False ☐ 5b Mismatch ☐ 5c Clamp (`!`) ☐ 5d No reply (`×`) ☐ 5e Row không Revert được ☐ 6 Revert / Revert all / Stop ☐ 6b Log: Export report, mở lại app vẫn còn ☐ 7 Từ chối serial sai; rút cáp giữa countdown ☐ 8 WING-Edit không bị đá + chụp màn hình ☐ 9 Settings ▸ Test connection

**Wave 4 (dán key DeepSeek, không ghi gì ra desk):** ☐ 1 Import cue sheet thật ☐ 2 Dạy 1 term (rút key) ☐ 3 Sửa Drum kit, Band đổi theo ☐ 4 AI Assistant, duyệt 1 thay đổi ☐ 5 Try AI ở Mapping ☐ 6 Lint file `.yaml` + Fix (.bak) ☐ 7 Scene cross-check ☐ 8 Test connection + `WING_DISABLE_LLM`

## 4. Ba việc thêm (~5 phút mỗi việc)
☐ **probe13** (nếu PR probe đã merge): `python docs/probes/probe13_nonascii_names.py 192.168.128.28 --out probe13.json`  — chỉ đọc, không ghi.
☐ **Scene tên có dấu:** trong WING-Edit đặt 1 channel tên `Ca sĩ Đức`, Save scene, bỏ file `.snap` vào `tests/data/`.
☐ **Limiter (§5.3):** mở menu dyn model trên WING-Edit, chép đủ danh sách model limiter: ____________________________

## 5. D-58 (tuỳ chọn)
Nếu có exe thử PySide6 6.12: bắt một AI call treo (Try AI, ngắt mạng), rồi ĐÓNG cửa sổ/app giữa lúc đó. Ghi: ☐ thoát sạch ☐ treo/crash — ______

## 6. Gửi lại
Ảnh tờ checklist đã tick · `probe13.json` · file `.snap` · danh sách limiter · ảnh chụp mọi bước ĐỎ (kèm số bước) · kết quả D-58 nếu có.
