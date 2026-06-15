# Checklist dựng Design System trong Figma

> Mục tiêu: dựng toàn bộ `docs/DESIGN_SYSTEM.md` thành **Variables + Styles + Components** trong Figma,
> sao cho **tên token trong Figma trùng tên CSS** → Figma MCP đọc ra là code khớp gần như tuyệt đối.
> Làm tuần tự từ trên xuống. Đánh dấu `[x]` khi xong.

---

## Giai đoạn 0 — Chuẩn bị file

- [ ] Tạo 1 file Figma tên `PharmaPredict — Design System`.
- [ ] Tạo 4 page: `🎨 Foundations` · `🧩 Components` · `📐 Templates` · `🖥️ Screens`.
- [ ] (Khuyến nghị) Bật **Dev Mode** + **MCP server** ngay để vừa dựng vừa kiểm tra MCP đọc đúng tên.

---

## Giai đoạn 1 — Variables (token màu, số) — quan trọng nhất cho MCP

> Dùng **Variables** (không phải Color Styles cũ) vì hỗ trợ **Modes** (light/dark) và tên gọi rõ.

### 1.1 Collection `color` — tạo 2 Mode: `Light` và `Dark`
Tạo từng variable (type Color), đặt tên **trùng token CSS bỏ dấu `--`**, dùng dấu `/` để gom nhóm:

- [ ] `primary`, `primary-hover`, `primary-soft`, `primary-contrast`
- [ ] `accent`, `accent-soft`
- [ ] `success`, `success-soft`, `warning`, `warning-soft`, `danger`, `danger-soft`
- [ ] `bg`, `surface`, `surface-muted`, `border`
- [ ] `text`, `text-muted`, `text-subtle`
- [ ] Điền giá trị cột **Light** và **Dark** theo §2.4–§2.5 của DESIGN_SYSTEM.md (token nào doc không liệt kê Dark thì để giá trị hợp lý hoặc giữ như Light).

### 1.2 Collection `number` — spacing, radius (1 mode)
- [ ] `space/1=4` `space/2=8` `space/3=12` `space/4=16` `space/5=24` `space/6=32` `space/7=48` `space/8=64`
- [ ] `radius/sm=8` `radius/md=12` `radius/lg=16` `radius/pill=999`

> ✅ Nghiệm thu GĐ1: chuyển Mode Light↔Dark, toàn bộ màu đổi theo. Tên variable đọc trong Dev Mode trùng token CSS.

---

## Giai đoạn 2 — Typography (Text Styles)

Tạo Text Style (Inter), tên trùng token §3:
- [ ] `text/display` 40/48 ExtraBold(800)
- [ ] `text/h1` 32/40 Bold(700)
- [ ] `text/h2` 24/32 Bold(700)
- [ ] `text/h3` 20/28 SemiBold(600)
- [ ] `text/body` 16/24 Regular(400)
- [ ] `text/sm` 14/20 Medium(500)
- [ ] `text/xs` 12/16 SemiBold(600), letter-spacing +0.08em, UPPERCASE (dùng cho eyebrow)
- [ ] Bật **tabular-nums** cho style hiển thị số (gauge, %): tạo thêm `text/number` nếu cần.

---

## Giai đoạn 3 — Effects (đổ bóng)

Tạo Effect Style §4:
- [ ] `shadow/sm` = 0 1 2 rgba(14,27,43,.06)
- [ ] `shadow/md` = 0 6 16 rgba(14,27,43,.08)
- [ ] `shadow/lg` = 0 18 40 rgba(11,95,181,.12)

---

## Giai đoạn 4 — Components (page 🧩 Components)

> Mỗi component: dựng 1 cái → chọn các bản thể → **Combine as variants** → đặt **Properties** đúng cột "Variants".
> Bắt buộc dùng **Auto Layout** + gán **Variables** cho fill/padding/radius (đừng hardcode số/màu).

### 4.1 Button
- [ ] Properties: `type` = primary/secondary/ghost/danger · `size` = md/sm · `state` = default/hover/disabled · boolean `icon`
- [ ] md cao 44, sm cao 36; padding ngang `space/4`; radius `radius/sm`; fill/màu chữ bằng variables
- [ ] Boolean `icon` để bật/tắt slot icon (Material Symbols)

### 4.2 Input / Textarea
- [ ] Properties: `state` = default/focus/error · boolean `leadingIcon`
- [ ] Border `border`; focus = ring `primary` 2px; error = border `danger` + text `danger`

### 4.3 Chip (triệu chứng)
- [ ] Properties: `state` = default/selected/disabled
- [ ] Pill (`radius/pill`); selected = fill `primary-soft` + border `primary` + text `primary`

### 4.4 Status Pill
- [ ] Properties: `tone` = success/warning/danger/neutral/secure
- [ ] Nền `*-soft`, chữ màu semantic, có icon trái

### 4.5 Card
- [ ] Properties: `kind` = default/featured/warning/dark
- [ ] radius `radius/md`, `shadow/md`, padding `space/5`; dark = fill `surface` mode dark hoặc nền primary đậm

### 4.6 Confidence Gauge ⭐ (đặc thù app)
- [ ] Properties: `level` = low/mid/high
- [ ] Donut/arc; màu theo §2.6 (low=danger, mid=warning, high=success); % ở giữa dùng `text/number`
- [ ] Kèm nhãn chữ "Thấp/Trung bình/Cao" (a11y — không chỉ dựa màu)

### 4.7 Prediction Bar
- [ ] Hàng: label nhóm thuốc + thanh tỉ lệ (fill `primary`) + % bên phải. Dựng để xếp top-3.

### 4.8 Nav item
- [ ] Properties: `state` = default/active · `device` = sidebar/bottom
- [ ] active = nền `primary-soft`, icon+chữ `primary`

### 4.9 Phụ trợ
- [ ] Avatar (`size` sm/md, pill, chữ viết tắt)
- [ ] Skeleton (block/line/card — fill `surface-muted`)
- [ ] Empty state (icon + `text/h3` + `text/body` muted)

> ✅ Nghiệm thu GĐ4: đổi Properties của mỗi component thấy đúng bản thể; đổi Mode Light/Dark component vẫn đúng màu.

---

## Giai đoạn 5 — Templates & Screens (page 📐 / 🖥️)

Lắp component thành màn theo §6 (grid, breakpoint). Dựng tối thiểu cho redesign toàn bộ:
- [ ] **Auth** (login/register/forgot/reset)
- [ ] **Trang chủ** (form bệnh án + side-stack metric/tip + hoạt động gần đây)
- [ ] **Kết quả** ⭐ (summary + Confidence Gauge sticky trái; detail-card + Prediction Bar phải)
- [ ] **Lịch sử** (search + grid history-card)
- [ ] **Hồ sơ** (account + feature-card + FAQ)
- [ ] Mỗi màn làm 2 khung: **Desktop (≥1024)** và **Mobile (<640, có bottom-nav)**
- [ ] Làm thêm các **trạng thái** §7: loading (skeleton), empty, error, "không đủ tin cậy"

---

## Giai đoạn 6 — Bàn giao cho code (qua Figma MCP)

- [ ] Mỗi màn/komponent đặt tên frame rõ ràng (vd `Screen/Result/Desktop`).
- [ ] Kiểm tra trong **Dev Mode**: chọn 1 frame → tên variable/style hiện ra **trùng token CSS**.
- [ ] Copy link frame → đưa cho Claude Code: *"Code lại frame này theo DESIGN_SYSTEM.md"*.
- [ ] Theo workflow nhóm: Codex đọc Figma lên checklist chuyển đổi → Claude code → Antigravity verify khớp Figma.

---

## Thứ tự ưu tiên (nếu thời gian gấp)

1. GĐ1 Variables (màu + dark mode) — **làm trước tiên, MCP cần nhất**
2. GĐ2 Typography + GĐ3 Effects
3. GĐ4: Button → Input → Chip → Status Pill → Card (5 cái cốt lõi)
4. GĐ4.6 Confidence Gauge + 4.7 Prediction Bar (linh hồn trang Kết quả)
5. GĐ5 màn Kết quả + Trang chủ trước, các màn còn lại sau.
