# Git/Jira Guide

Hiện tại dự án đã tới SCRUM-45 tương ứng Task 14.

## Commit bổ sung UI/UX Figma
```bash
git add README.md docs/UI_UX_FIGMA.md
git commit -m "[SCRUM-46] Bo sung tai lieu UI UX Figma"
git push origin main
```

## Commit hoàn thiện CRUD Nhóm thuốc
Phần này bổ sung PUT API và nút Sửa cho Task 13/14.

```bash
git add backend/app.py frontend/script.js
git commit -m "[SCRUM-46] Hoan thien chuc nang sua nhom thuoc"
git push origin main
```

## Tiếp tục Task 15
Task 15 là tạo bảng Thuoc và thiết lập khóa ngoại với NhomThuoc. File models.py hiện đã có class Thuoc và ForeignKey nhom_thuoc_id, vì vậy khi sang SCRUM-47 có thể commit:

```bash
git add backend/models.py
git commit -m "[SCRUM-47] Tao bang Thuoc va khoa ngoai voi NhomThuoc"
git push origin main
```
