# Ghi chú tiến độ SCRUM-59 / Task 28 và UI/UX Figma

## 1. Tiến độ hiện tại

Theo trao đổi nhóm, dự án đang triển khai tới:

```text
SCRUM-59 / Task 28
```

Task 28:

```text
Viết Unit Test kiểm tra logic các hàm tiền xử lý văn bản.
```

Các phần UI/UX Figma bổ sung trong thư mục docs không làm thay đổi logic Task 28.

## 2. Những file tài liệu UI/UX đã bổ sung

```text
docs/UI_UX_FIGMA.md
docs/DESIGN_SYSTEM.md
docs/UI_UX_90_95_COMPLETION.md
docs/FIGMA_PAGE_COPY_CONTENT.md
docs/TASK_28_STATUS_AND_UIUX_NOTE.md
```

Các file này chỉ dùng làm tài liệu minh chứng, không thay đổi backend, frontend, database hoặc test hiện có.

## 3. Liên quan Jira / Backlog

Phần UI/UX Figma liên quan tới các task:

- Task 1: Thiết kế UI trang đăng nhập trên Figma.
- Task 24: Thiết kế Wireframe/Prototype khu vực nhập bệnh án trên Figma.
- Task 25: Dựng UI Textarea nhập bệnh án.
- Task 35: UI hiển thị Top 3 nhóm thuốc.

Không nên gán các file tài liệu này là Task 28, vì Task 28 là Unit Test xử lý văn bản.

## 4. Commit message khuyên dùng

Nếu Jira có ticket riêng cho UI/UX Figma, dùng đúng mã ticket đó.

Ví dụ:

```bash
git add docs/UI_UX_90_95_COMPLETION.md docs/FIGMA_PAGE_COPY_CONTENT.md docs/TASK_28_STATUS_AND_UIUX_NOTE.md
git commit -m "[SCRUM-XX] Bo sung minh chung UI UX Figma"
git push origin main
```

Nếu không có ticket riêng, có thể commit dạng tài liệu:

```bash
git add docs/UI_UX_90_95_COMPLETION.md docs/FIGMA_PAGE_COPY_CONTENT.md docs/TASK_28_STATUS_AND_UIUX_NOTE.md
git commit -m "docs: bo sung minh chung UI UX Figma"
git push origin main
```

## 5. Cam kết không ảnh hưởng code cũ

Các file trên thuộc thư mục docs, chỉ là Markdown tài liệu. Không sửa:

```text
backend/
frontend/
models/
scripts/
tests/
requirements.txt
package.json
```

Vì vậy không ảnh hưởng các chức năng đã hoàn thành từ Task 1 đến Task 28.
