# 04 — Cấu hình model AI (DeepSeek)

Phần model chỉ làm **2 việc nhỏ**: đề xuất mapping cột khi import kịch bản, và
đoán thuật ngữ chưa có trong từ vựng. Mọi phần còn lại của tool không cần model.

## Cách 1 — dán key vào `provider.yaml` (khuyến nghị)

File `provider.yaml` ở **thư mục gốc dự án** đã tạo sẵn. Chỉ cần:

1. Lấy key tại <https://platform.deepseek.com> → **API Keys** → Create new key.
2. Mở `provider.yaml`, thay dòng cuối:

```yaml
api_key: sk-xxxxxxxxxxxxxxxxxxxxxxxx
```

3. Lưu file. Xong — chạy lại lệnh import là model tự vào việc.

> File này đã nằm trong `.gitignore` — key **không bao giờ** vào git.

Key dán qua **Tools ▸ Settings** của app desktop được ghi vào một
`provider.yaml` **trong thư mục knowledge** — mặc định `%USERPROFILE%\.config\wing-skill`
khi chạy bản `.exe`, hoặc thư mục mà `WING_KNOWLEDGE_DIR` trỏ tới nếu anh đặt
biến đó. Cả app lẫn lệnh `wing showcontext import` đều đọc bản này, nên dán một
lần là cả hai cùng có key.

Khi cả hai file cùng tồn tại: bản trong thư mục knowledge **thắng** file ở gốc
dự án — nhưng chỉ khi nó thật sự có key dùng được (ô key để trống thì bỏ qua,
đi tiếp xuống file gốc). Và `WING_PROVIDER_CONFIG` thắng tất cả: đã trỏ vào file
nào thì đọc đúng file đó.

## Cách 2 — biến môi trường (khi không muốn key nằm file)

```bash
$env:DEEPSEEK_API_KEY = "sk-xxxx"    # PowerShell, chỉ hiệu lực cửa sổ hiện tại
wing showcontext import "Kich ban.xlsx"
```

Khi cả hai cùng có, **key trong file thắng** env var (vì ai sửa file vừa rồi
chắc chắn muốn dùng nó).

## Các lựa chọn trong `provider.yaml`

| Key | Ý nghĩa | Mặc định |
|---|---|---|
| `provider:` | `openai-compat` hoặc `anthropic` | `anthropic` |
| `base_url:` | endpoint API | DeepSeek: `https://api.deepseek.com` |
| `model:` | tên model theo tài khoản của anh | `deepseek-chat` |
| `api_key:` | key dán trực tiếp | trống |
| `api_key_env:` | tên biến môi trường chứa key | `DEEPSEEK_API_KEY` / `ANTHROPIC_API_KEY` |

Đổi provider khác tương thích OpenAI (OpenAI chính hãng, server local…): chỉ
sửa `base_url` + `model`. Đổi sang Anthropic: đặt `provider: anthropic`, cài
`pip install -e .[llm]`.

## Tắt model tạm thời

```bash
$env:WING_DISABLE_LLM = "1"     # phiên này: mọi lệnh bỏ qua model
Remove-Item Env:\WING_DISABLE_LLM
```

Không key / mất mạng / kill-switch bật → lệnh in một dòng báo rõ rồi chuyển
hướng thủ công. Không bao giờ lỗi giữa chừng vì thiếu model.

## Kiểm tra cấu hình

```bash
wing showcontext import "tests/data/BIDV TPHCM - KỊCH BẢN SK YEP 2025..xlsx" --one-shot
```

Có key: file `BIDV ... .map.yaml` hiện ra với `header_row: 5`, cột Nội dung đã
map. Không key: thấy dòng `(no model assist: ...)`.
