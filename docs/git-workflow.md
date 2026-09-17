# Quy trình Git — GitHub-oriented

Từ 2026-09-15 repo này làm việc qua GitHub, không còn commit thẳng vào
`main` local nữa. Lý do: `main` local từng đi trước `origin/main` 52 commit
suốt ba tuần — công việc có làm, nhưng không ai nhìn thấy, không có CI chạy,
và không có chỗ nào để review trước khi nó thành lịch sử.

Remote: <https://github.com/toanaz-ops/project008-soundtech-assist> (public).

## Luật bất di bất dịch

1. **`main` chỉ đổi qua một PR đã merge trên GitHub.** Không commit thẳng,
   không merge local rồi push. Không bao giờ force-push `main`.
2. **Mỗi task = một nhánh trong worktree riêng** dưới `.claude/worktrees/`.
   Tên nhánh: `feat/…`, `fix/…`, `chore/…`, `docs/…`.
3. **`git add` luôn liệt kê đường dẫn tường minh.** Không `git add .`,
   không `git add -A`.
4. **CI phải xanh** trước khi nói tới merge. Check bắt buộc tên là `test`.
5. **Một agent verifier mới phải cố bác bỏ** lời tuyên bố "xong" — đọc file
   thật, chạy lệnh thật — trước khi mở lời xin merge (luật toàn cục 1 và
   "never grade your own work").
6. **Người bấm Merge là ToanAZ**, trừ khi anh đã nói "merge" trong chính
   cuộc hội thoại đang chạy.
7. **Merge bằng merge commit, không squash.** Từng commit của từng task và
   commit của vòng review-toàn-nhánh đều phải sống sót trong lịch sử.

## Một vòng làm việc

Tạo worktree + nhánh (chạy từ máy, sửa `<slug>` và tiền tố cho đúng):

```bash
git -C "D:\DEV CAVE EP3\PROJECT008-SOUNDTECH-ASSIST" worktree add "D:\DEV CAVE EP3\PROJECT008-SOUNDTECH-ASSIST\.claude\worktrees\<slug>" -b feat/<slug> main
```

Làm việc trong worktree đó. Commit với đường dẫn tường minh:

```bash
git add wing_parser/ui/doctor_page.py tests/test_ui_doctor.py
```

```bash
git commit -m "feat(ui): <mô tả một dòng>"
```

Đẩy sớm — đừng đợi tới lúc xong mới push:

```bash
git push -u origin feat/<slug>
```

Mở PR (body soạn sẵn ra file để giữ xuống dòng):

```bash
gh pr create --base main --title "feat(ui): <tiêu đề>" --body-file .git/pr-body.md
```

Xem CI chạy:

```bash
gh pr checks <số PR> --watch --interval 30
```

CI đỏ thì đọc đúng chỗ hỏng, sửa trên chính nhánh đó rồi push lại:

```bash
gh run view <run id> --log-failed
```

Sau khi ToanAZ bấm Merge trên GitHub, kéo về máy:

```bash
git -C "D:\DEV CAVE EP3\PROJECT008-SOUNDTECH-ASSIST" pull --ff-only
```

Rồi dọn worktree đã xong:

```bash
git -C "D:\DEV CAVE EP3\PROJECT008-SOUNDTECH-ASSIST" worktree remove ".claude/worktrees/<slug>"
```

## CI chạy cái gì

`.github/workflows/ci.yml` — chạy trên `pull_request` và `push` vào `main`,
một job tên `test` trên `windows-latest` (sản phẩm là exe Windows), Python
3.12, cài `pip install -e ".[dev,ui,ingest,llm,llm-openai]"` rồi
`python -m pytest`.

Qt chạy headless bằng `QT_QPA_PLATFORM=offscreen:configfile=.github/ci-offscreen-screen.json`.
Cần file cấu hình vì màn hình ảo mặc định của `offscreen` chỉ 800x800, cắt
âm thầm mọi cửa sổ rộng hơn (test state-store resize 1010 đọc về 798).
Đường dẫn phải là **tương đối**: Qt cắt chuỗi platform ở dấu `:`, đường dẫn
tuyệt đối kiểu `C:\...` làm tiến trình chết câm không một dòng lỗi.

Extra `mcp` **cố ý không cài**: `tests/test_mcp.py` có một test chỉ chạy khi
`mcp` vắng mặt (kiểm tra thông báo lỗi của `wing-mcp`), và một test khác
`importorskip("mcp")`. Cài thêm `mcp` không tăng số test chạy, chỉ đổi test
nào bị skip.

## Định nghĩa xong

Một task chỉ được gọi là xong khi có đủ:

- Lệnh và output đã dán vào hội thoại (luật toàn cục 1) — không dán thì ghi
  "chưa verify".
- Docs/spec đã cập nhật nếu hành vi đổi.
- Commit có đường dẫn tường minh, nhánh đã push.
- **URL của PR** dán ra được.
- **CI xanh** trên đúng PR đó — dán URL của run, không chỉ nói "pass".
- Một agent verifier mới đã thử bác bỏ và không bác được.
- Tính năng người dùng chạm tới: đã có nút trong `wing-ui`, không phải
  CLI-only (xem `CLAUDE.md`).

Merge là việc của ToanAZ. Agent dừng lại ở bước "PR xanh, mời anh xem".

## Ghi nhận 2026-09-17

- Bốn PR đầu tiên (#1–#4, GUI wave 2) đi hết quy trình này, merge vào `main` tại `dcf897a`.
- Bài học 1: đổi base của PR KHÔNG tự kích CI lại — phải push một commit rỗng (`git commit --allow-empty`) để trigger.
- Bài học 2: một PR xếp chồng (stacked) mà base của nó vừa merge thì cần `git merge origin/main` cục bộ trước khi push tiếp — nhất là khi hai PR cùng sửa `memory/MEMORY.md` (dễ conflict).

## Branch protection cho `main`

Cấu hình nằm ở `.github/branch-protection.json` (bắt buộc PR + check `test`, cấm force-push và xóa nhánh). Áp dụng (một lần, hoặc sau khi sửa file):

```bash
gh api -X PUT repos/toanaz-ops/project008-soundtech-assist/branches/main/protection --input .github/branch-protection.json
```
