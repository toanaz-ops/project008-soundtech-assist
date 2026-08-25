# 01 — Đưa kịch bản chương trình vào hệ thống

Producer gửi kịch bản (running order / cue sheet) dạng Excel. Lệnh
`wing showcontext import` biến nó thành file show-context mà rule tư vấn đọc được.

## Cách nhanh nhất — wizard tương tác

```bash
wing showcontext import "Kich ban BIDV.xlsx"
```

Nếu đã dán key vào `provider.yaml` (xem [04](04-cau-hinh-model.md)), model sẽ:

1. Đọc ~20 dòng đầu **mỗi sheet**, tự chọn sheet nào là rundown (bỏ qua sheet rác).
2. Tìm dòng header (thường là dòng 4–5, không phải dòng 1).
3. Đề xuất cột nào là STT / thời gian / nội dung / performers / âm thanh / ánh sáng…

Anh chỉ cần **Enter để chốt** từng nhóm, hoặc gõ đè khi đề xuất sai. Mỗi câu hỏi
hiện sẵn `[giá trị đề xuất]` — Enter = nhận.

Cuối cùng wizard lưu `Tên-file.map.yaml` (mapping để lần sau khỏi hỏi lại) rồi
xuất show-context.

> Model chỉ ĐỀ XUẤT. Mọi đề xuất được kiểm chứng lại với file Excel thật trước
> khi đưa ra cho anh; import không bao giờ dùng mapping chưa kiểm chứng.
> Thuật ngữ performer nào từ vựng chưa có → model đoán và **chỉ ghi lại khi anh
> gõ `y`**. Không key / mất mạng → tự chuyển sang hỏi tay từng cột, không lỗi.

## Khi cần gọn — `--one-shot`

```bash
wing showcontext import "Kich ban BIDV.xlsx" --one-shot
```

Chỉ ghi ra `Kich ban BIDV.map.yaml` (đề xuất của model) rồi dừng. Anh mở ra sửa
tay, sau đó dùng bước 2 dưới đây.

## Dùng mapping có sẵn

```bash
wing showcontext import "Kich ban BIDV.xlsx" --map "Kich ban BIDV.map.yaml" -o bidv-show.yaml
```

- `--map` : file mapping (một khách hàng recurring giữ một file, dùng mãi)
- `-o`    : ghi ra file thay vì in màn hình
- `--scene examples/scene.snap` : kèm đề xuất cue từ scene (dạng comment)

Luồng này 100% offline — không bao giờ gọi model.

## Kiểm tra kết quả

```bash
wing showcontext lint bidv-show.yaml          # soi lỗi cấu trúc
wing doctor --show bidv-show.yaml scene.snap  # chạy rule Q1–Q7 với show context
```

## Từ vựng (`cuesheet:`)

Thuật ngữ như "Nhạc đón khách", "ca sĩ nữ", "PG" được tra trong
`knowledge/toanaz/classifier.yaml` mục `cuesheet:`. Hiện tại vocabulary còn
trống — trong lúc import, model sẽ đề nghị bổ sung từng từ và anh chốt. File
này sửa tay được; comment anh thêm được giữ nguyên mọi lần ghi lại.
