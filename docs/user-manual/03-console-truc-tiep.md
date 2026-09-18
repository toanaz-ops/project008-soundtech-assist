# 03 — Làm việc với console đang bật

Mọi lệnh `net` chạy **song song** với WING-Edit và Companion — không chiếm
kết nối, không đá nhau (yêu cầu bắt buộc, đã nghiệm thu trên console thật
2026-08-23). IP mặc định của desk: `192.168.128.28`.

## Đọc

```bash
wing net identity 192.168.128.28     # tên, model, serial, firmware
wing net snapshot 192.168.128.28 -o show.snap   # đọc toàn bộ console ra file .snap
wing net get 192.168.128.28 /ch/01/fader        # đọc một lá đơn
```

> **Trên UI (wing-ui):** trang **Console** (Ctrl+7) có nút **Connect** —
> bấm vào là chạy đúng `wing net identity` (bắt tay hỏi tên desk), và nút
> **Pull** ở khối SNAPSHOT — chạy `wing net snapshot`, đọc cả console vào
> bộ nhớ rồi bấm **Export to .snap...** để ghi ra file, tương đương `-o`.
> Riêng `wing net get` — đọc một lá đơn — **vẫn không có nút trên UI, cố
> ý**: trang Console chỉ đọc những gì luồng show cần (kết nối, dò schema,
> đọc cả console, theo dõi), không có ô tra một địa chỉ lẻ. Từ wave 3 UI
> **có** ghi được — nhưng chỉ qua nút **Repair** của một finding, xem mục
> "Ghi từ UI" bên dưới.

Sau khi có `.snap`, mọi lệnh ở [02](02-phan-tich-scene.md) dùng được ngay:
`wing doctor show.snap`.

## Ghi — luôn dry-run trước

```bash
wing net set 192.168.128.28 /ch/01/fader -12.5          # CHỈ HIỆN, chưa gửi gì
wing net set 192.168.128.28 /ch/01/fader -12.5 --confirm # mới gửi thật
wing net toggle 192.168.128.28 /ch/03/mute --confirm
wing net push 192.168.128.28 show.snap --confirm         # đẩy cả scene
```

Không có `--confirm` thì **không có gì được gửi** — an toàn để tập.

> **Trên UI:** bốn lệnh `net set` / `toggle` / `push` / `get` **vẫn không
> có nút nào cả, và đó là cố ý** — đừng đi tìm. UI ghi được từ wave 3,
> nhưng theo một đường khác hẳn: chỉ **một tham số mỗi lần**, và chỉ từ
> nút **Repair** của một finding trong trang Doctor (mục "Ghi từ UI" bên
> dưới). Muốn gõ thẳng một địa chỉ, lật một toggle, hay đẩy cả scene —
> vẫn phải ra CLI với `--confirm`.

## Ghi từ UI — một tham số một lần (wave 3)

Từ wave 3, nút **Repair** trong trang **Doctor** không chỉ sửa scene trong
bộ nhớ nữa: nó có thể gửi thẳng ra console đang bật. Mỗi lần gửi **đúng
một lá OSC** — không có `push`, không gộp nhiều tham số vào một gói.

### 1. Nạp đạn trước đã (Arm)

Bên cạnh khu repair có ô chọn **Apply to console** và nút **Arm**. Khi
chưa arm, ô chọn đọc **Manual**, còn **Delayed** và **Immediate** bị làm
mờ — không bấm được. Bấm **Arm** mở hộp thoại hỏi ba điều, phải đủ cả ba:

1. App **hỏi lại tên desk ngay lúc đó** (chạy đúng `wing net identity`),
   không xài lại tên từ lần Connect trước — vì cái sắp tin là "đây đúng
   là console tôi định ghi".
2. Tick ô **"This desk is NOT running a show right now."** — ô này mặc
   định **bỏ trống**. Tick nghĩa là "desk đang KHÔNG chạy show".
3. **Gõ đúng tên console** vào ô xác nhận. Sai một ký tự là nút Arm vẫn mờ.

Arm xong, nút đổi thành nhãn **Armed: {tên desk}** và cả ba mức chọn được.

**Arm chết theo kết nối.** Disconnect, mất desk (`LOST`), lỗi (`ERROR`),
hay đóng app — tất cả đều gỡ arm, ô chọn tự rơi về **Manual**. Nhìn lên
sau một cú rớt mạng là thấy đúng sự thật, không phải mức đã chọn lúc trước.

### 2. Ba mức gửi

| Mức | Bấm Repair thì sao |
|---|---|
| **Manual** | Chỉ sửa scene trong bộ nhớ. Không gì ra desk. Muốn gửi thì bấm nút **Send to console** trên đúng dòng đó trong khối **Changes** — và nó mở đồng hồ đếm ngược y như Delayed. |
| **Delayed** | Sửa scene **và** mở đồng hồ đếm ngược ngay. |
| **Immediate** | Sửa scene **và** gửi luôn, không hộp thoại nào. Dành cho lúc soundcheck, mắt đang nhìn desk chứ không nhìn laptop. |

Nút **Send to console** chỉ mờ khi **chưa kết nối** (trang Console không ở
`CONNECTED`/`WATCHING`), tooltip nói rõ `Connect to the console (Ctrl+7) to
send this.` Chưa arm thì nút **vẫn bấm được** — bấm vào là hộp thoại Arm
hiện ra trước, rồi mới tới đồng hồ.

### 3. Đồng hồ đếm ngược — ba nút

Hộp thoại đếm ngược cho xem, trước khi gói tin rời máy: địa chỉ OSC,
**desk đang giữ giá trị gì** (đọc sống, không lấy từ file), **file scene
tưởng là gì**, và **nó sẽ thành gì**. Hai giá trị đầu lệch nhau thì có
thêm dòng cảnh báo ⚠ — ai đó đã chỉnh desk sau khi mình pull scene; xử lý
ra sao là quyết định của người đứng máy, app không tự đoán.

- **Apply now** — gửi ngay, không đợi hết giờ.
- **+5 s** — cộng thêm 5 giây vào phần còn lại, bấm bao nhiêu lần cũng
  được, không giới hạn. Cần một phút thì bấm mười hai cái.
- **Cancel** — **không gửi gì cả**. Nhưng **sửa trong scene vẫn còn** —
  Repair đã xảy ra rồi. Muốn bỏ luôn phần file thì bấm **Undo** trong khối
  Changes. Hai cái cửa khác nhau.

**Hết giờ là gửi.** Đồng hồ chạy về 0 mà không ai bấm gì thì nó apply —
đó là ý nghĩa của "delayed", không phải "hủy".

Số giây mặc định lấy từ **Tools ▸ Settings ▸ Default apply delay (s)**
(3–60, mặc định 5), và được nhớ giữa các lần mở app.

### 4. Ba huy hiệu kết quả — và scene đổi theo cách khác nhau

Mọi lệnh ghi đều **đọc lại** (read-back) sau khi gửi, vì WING có thể kẹp
(clamp) một giá trị ngoài tầm mà **vẫn trả lời `OK`**. Ba kết cục, không
phải hai:

| Huy hiệu | Nghĩa | Scene trong app thành gì |
|---|---|---|
| **✓ sent** | Desk xác nhận đúng giá trị vừa gửi. | Lá scene đặt bằng **giá trị vừa gửi** (đúng cái đồng hồ đã hiện). |
| **⚠ clamped** | Desk trả về **một giá trị khác** — nó đã kẹp lại. | Lá scene đặt bằng **giá trị desk thật sự đang giữ**, để Doctor chấm lại theo sự thật của desk. |
| **✗ no reply** | Desk **không trả lời** đọc lại. Gói tin có thể đã tới, có thể chưa — không ai biết. | Lá scene **để nguyên như Repair vừa đặt**. Bịa một giá trị cho một cái desk im lặng còn tệ hơn là thừa nhận không biết. |

### 5. Sổ đã gửi, và đường về

Dưới danh sách Changes có khối **Sent to console**: mỗi tham số đã ghi
trong phiên này một dòng — địa chỉ, **giá trị desk giữ TRƯỚC khi ghi**,
giá trị đã ghi, và kết quả đọc lại. Dòng ở đây **không mất khi bấm Undo**,
vì Undo là chuyện của file; một thay đổi trên desk mà UI không gỡ được thì
tệ hơn là một danh sách dài.

- **Revert** (từng dòng) — ghi ngược lại giá trị desk giữ trước đó, **qua
  đúng mức đang chọn**: Immediate thì gửi luôn, Manual và Delayed đều đi
  qua đồng hồ đếm ngược.
- **Revert all** — đi **ngược thứ tự**: ghi sau, gỡ trước. Vẫn **một tham
  số một gói tin**: cái sau chỉ bắt đầu khi cái trước đã có đọc lại. Dòng
  tiến độ đếm `Reverting 3/7: /ch/...`. Ở mức Delayed thì **mỗi tham số
  một đồng hồ** — chậm có chủ ý, đúng cái "delayed" đã hứa.
- **Stop** — dừng giữa chừng, **giữa hai tham số**. Cái đang trên dây vẫn
  chạy hết, vì không có cách nào rút một gói tin đã bay đi. Ở mức Delayed
  thì đường ra là nút **Cancel** của chính đồng hồ (Stop nằm sau hộp thoại
  modal, bấm không tới).

Revert thành công thì **scene cũng lùi về theo**, nên **finding sẽ hiện
lại** trong Doctor — đúng, vì desk thật sự đã về lại trạng thái mà luật
phàn nàn. Còn **dòng journal thì KHÔNG bị gỡ**: journal là ghi chép phía
file về điều người đứng máy đã quyết, Undo vẫn nằm riêng ở đó.

### 6. Vì sao gói tin không thể đi khi mình chưa muốn

Năm cái cổng, mỗi cổng chặn một kiểu nhầm: chỉ ghi khi trang Console đang
`CONNECTED`/`WATCHING`; phải arm trước; đồng hồ hoặc nút Send là bước xác
nhận; **ngay trước khi gói tin rời máy** app hỏi lại cả hai cổng đầu (desk
rớt giữa lúc đếm ngược thì hiện `The console connection dropped. Nothing
was sent.`); và ngay trước khi gửi, app **hỏi lại
identity một lần nữa** — serial khác với lúc arm là **từ chối, không gửi**
(một cái desk khác đã nhảy vào địa chỉ IP đó giữa chừng). Nếu có đặt biến
môi trường `WING_WRITE_ALLOW_SERIAL`, `net/write.py` còn kiểm thêm một
tầng nữa ở dưới cùng.

## Theo dõi thay đổi trực tiếp

```bash
wing net watch 192.168.128.28 --until 120    # theo dõi 120 giây rồi dừng
wing net watch 192.168.128.28 --json         # máy đọc được, Ctrl+C để dừng
wing net watch 192.168.128.28 --interval 0.5 # chủ động giãn chu kỳ poll
```

> **Trên UI:** khối DISCOVERY có nút **Discover** — dò cây schema để dựng
> danh sách theo dõi (tương đương bước dò ngầm mà `wing net watch` tự làm
> trước khi poll); xong thì khối WATCH có nút **Start watch** — chạy
> đúng `wing net watch`, kết quả đổ thẳng vào bảng sự kiện trên trang
> thay vì in ra terminal. Không có ô gõ `--until`/`--json`; khoảng poll
> chỉnh bằng ô Interval bên cạnh nút.

Đã đo trên console thật: ~150 sự kiện trong 120s, mỗi kéo fader từ WING-Edit
hiện sau ~250 ms; hai phần mềm đứng cạnh nhau không xung đột.

> Mẹo: nếu lần mở đầu `watch` báo thiếu cả family lá (unresolved families),
> **chạy lại** trước khi tin kết quả — lỗi tạm thời của quá trình dò schema,
> tool tự báo rõ chứ không giấu.
