# Brief cho Codex — Plan redesign giao diện PharmaPredict

> Đội trưởng dán nội dung "Task" bên dưới cho **Codex CLI** để nó output plan dạng checklist Markdown.
> Sau khi có plan, Claude Code review/confirm rồi mới code (theo team workflow).

## Bối cảnh

- Frontend: **HTML/CSS/JS thuần** tại `frontend/index.html`, `frontend/styles.css`, `frontend/script.js`. Không framework, không build step.
- App y tế: gợi ý nhóm thuốc từ triệu chứng tiếng Việt. 4 trang (Trang chủ, Kết quả, Lịch sử, Hồ sơ) + màn auth.
- Đã có sẵn 2 tài liệu nền — plan PHẢI bám theo:
  - `docs/DESIGN_SYSTEM.md` (token màu/typography/spacing/component, có dark mode + thang độ tin cậy)
  - `docs/FIGMA_BUILD_CHECKLIST.md`

## Phạm vi

Redesign **toàn bộ** UI theo design system mới (light + dark mode), giữ nguyên logic JS/hành vi hiện có.

## Ràng buộc bắt buộc

1. Vanilla HTML/CSS/JS — không thêm framework/bundler.
2. **Giữ nguyên các `id` JS đang dùng** (vd `#diagnosis-form`, `#confidence-bar`, `#result-title`, `#symptom-list`…) để không vỡ `script.js`. Class trình bày có thể đổi.
3. Khai báo toàn bộ token trong `:root` + khối `[data-theme="dark"]`; thêm nút toggle dark mode (lưu localStorage).
4. Accessibility: tương phản ≥4.5:1, focus ring, `aria-label` cho icon-button, không truyền tin chỉ bằng màu.
5. Mỗi thay đổi phải Antigravity verify được trên browser trước khi merge.

## Yêu cầu với PLAN (Codex output)

Plan dạng checklist Markdown, chia theo:
- **Giai đoạn 0 — Tokens & nền tảng**: khai báo CSS variables, dark mode toggle, refactor base.
- **Giai đoạn 1 — Component CSS dùng lại**: button, input, chip, status-pill, card, nav, gauge độ tin cậy, prediction bar, skeleton, empty state.
- **Giai đoạn 2 — Từng trang**: Auth → Trang chủ → Kết quả ⭐ → Lịch sử → Hồ sơ. Mỗi trang ghi rõ thay đổi layout + rủi ro chạm vào JS.
- **Giai đoạn 3 — Responsive & trạng thái**: desktop/tablet/mobile, loading/empty/error/"không đủ tin cậy".
- **Giai đoạn 4 — QA**: checklist để Antigravity verify (đối chiếu Figma + a11y).

Mỗi mục cần: file đụng tới, mô tả ngắn, và đánh dấu rủi ro nếu chạm logic JS.
Ưu tiên: GĐ0 → component → **trang Kết quả** (quan trọng nhất) → các trang còn lại.

---

## Task (dán cho Codex)

```
Lập plan redesign toàn bộ giao diện frontend của project PharmaPredict (HTML/CSS/JS thuần trong thư mục frontend/).
Bám theo docs/DESIGN_SYSTEM.md và docs/FIGMA_BUILD_CHECKLIST.md. Output plan dạng checklist Markdown theo cấu trúc
Giai đoạn 0→4 mô tả trong docs/CODEX_REDESIGN_BRIEF.md. Ràng buộc: giữ nguyên mọi id JS đang dùng trong frontend/script.js,
không thêm framework, thêm dark mode toggle, đảm bảo a11y. Mỗi mục ghi rõ file đụng tới và rủi ro chạm logic JS.
```
