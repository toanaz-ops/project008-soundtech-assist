# 05 — Thư viện kiến thức mix

Kho kiến thức mix có nguồn trích dẫn: EQ, dynamics, reverb/delay, nhạc cụ,
giọng hát và giọng nói, automix, feedback, monitor, micro, hệ thống, thể loại
và Behringer WING. Mỗi mục có tóm tắt, bài viết, biểu đồ, video tham khảo và
danh sách nguồn đánh số. Automix của dự án cũng đọc từ kho này.

## Ba chỗ để đọc

| Ở đâu | Cách mở | Sửa được không |
|---|---|---|
| App desktop | `wing-ui` → trang **Thư viện** (Ctrl+9) | Có |
| Artifact (điện thoại, mọi nơi) | https://claude.ai/artifact/BybrQHwxSg34fR3mgf7Rv5 | Không (bản chụp chỉ đọc) |
| Web công ty | https://master.azsoundtech.com/library/ (đăng nhập PRJ012) | Chủ dự án: có. Nhân viên: chỉ xem |

## Trong app

1. Gõ vào ô tìm kiếm (không cần dấu: "dong bo" tìm được "đồng bộ").
2. Đổi **Nhóm theo**: Chủ đề / Nhạc cụ / Thể loại / Kỹ thuật / Nguồn.
3. Bấm một mục để đọc. Nhãn đỏ **THIẾU NGUỒN** và vàng **NGUỒN CHƯA KIỂM
   DUYỆT** nghĩa là cần xem lại nguồn.
4. **Sửa** (hoặc **Mục mới**): phải có ít nhất một nguồn đủ (tiêu đề, nhà
   xuất bản, loại, URL hoặc sách, ngày truy cập) và một ghi chú thay đổi, nút
   Lưu mới bật. Duyệt xong một mục thì đổi Trạng thái sang `reviewed`.
5. **Lịch sử** xem ai sửa gì, khi nào, kèm diff; khôi phục một bản cũ sẽ tạo
   một bản mới (lịch sử không bao giờ bị xoá).
6. **Ngưng dùng** ẩn một mục (không xoá); tick "Hiện mục đã ngưng" để thấy lại.
   (Nhãn ở đây theo giao diện tiếng Việt; tiếng Anh là New entry / Edit /
   History / Retire.)

Bài anh sửa trong app nằm ở `%USERPROFILE%\.config\wing-skill\library\`
(lớp "của anh"); bản exe mới vẫn mang mục mới, nhưng mục anh đã sửa thì
giữ bản của anh.

## Cho agent và dòng lệnh

```bash
wing library search "kick eq" --json
```

```bash
wing library show eq-hpf-every-channel
```

```bash
wing library validate
```

Agent thêm/sửa bằng `wing library add FILE --author agent:<tên>` hoặc
`wing library edit ID FILE --author agent:<tên> --note "<lý do>"` (file phải
có `revision` hiện tại). Định dạng: `knowledge/library/SCHEMA.md`.
