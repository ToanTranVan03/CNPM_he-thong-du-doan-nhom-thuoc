# PharmaPredict — Design System v1

> Nguồn chân lý thiết kế cho redesign toàn bộ. Dùng chung cho **Figma** (Dev Mode) và **code** (`frontend/styles.css`).
> Quy ước: tên token giữ nguyên giữa Figma ↔ CSS để đồng bộ qua Figma MCP.

---

## 1. Nguyên tắc thiết kế (Design Principles)

1. **Tin cậy y khoa (Clinical trust)** — tông xanh trầm, sạch, nhiều khoảng trắng có chủ đích. Không lòe loẹt.
2. **Phân cấp rõ ràng** — một màu nhấn duy nhất (cam) chỉ dành cho cảnh báo & CTA chính. Mọi thứ khác là nền/xám/xanh.
3. **Dữ liệu là trung tâm** — trang Kết quả phải đọc được trong 3 giây: chẩn đoán → độ tin cậy → nhóm thuốc.
4. **An toàn mặc định** — luôn hiển thị disclaimer; trạng thái "không đủ tin cậy" phải rõ ràng, không gây hiểu nhầm là chẩn đoán chắc chắn.

---

## 2. Màu sắc (Color Tokens)

### 2.1 Brand & Primary
| Token | Light | Vai trò |
|-------|-------|---------|
| `--primary` | `#0B5FB5` | Màu thương hiệu, nút chính, link active |
| `--primary-hover` | `#0A4F97` | Hover nút chính |
| `--primary-soft` | `#D7E6FB` | Nền nhấn nhẹ, chip active |
| `--primary-contrast` | `#FFFFFF` | Chữ trên nền primary |

### 2.2 Accent (chỉ dùng cho nhấn mạnh có chủ đích)
| Token | Light | Vai trò |
|-------|-------|---------|
| `--accent` | `#E8722B` | CTA quan trọng nhất, highlight cảnh báo nhẹ |
| `--accent-soft` | `#FCE8D8` | Nền badge accent |

### 2.3 Semantic
| Token | Light | Vai trò |
|-------|-------|---------|
| `--success` | `#1B8A5A` | Độ tin cậy cao, "Đã lưu" |
| `--success-soft` | `#DAF1E6` | Nền badge success |
| `--warning` | `#B7791F` | Độ tin cậy trung bình, cần xem lại |
| `--warning-soft` | `#FBF0D6` | Nền badge warning |
| `--danger` | `#C0392B` | Cảnh báo nghiêm trọng, lỗi |
| `--danger-soft` | `#FBE3E0` | Nền badge danger |

### 2.4 Surfaces & Text (Light)
| Token | Light | Vai trò |
|-------|-------|---------|
| `--bg` | `#F5F7FB` | Nền trang |
| `--surface` | `#FFFFFF` | Card, panel |
| `--surface-muted` | `#EEF2F8` | Vùng phụ, input nền |
| `--border` | `#DCE3ED` | Đường viền, divider |
| `--text` | `#0E1B2B` | Chữ chính |
| `--text-muted` | `#5A6675` | Chữ phụ, label |
| `--text-subtle` | `#8A95A3` | Placeholder, caption |

### 2.5 Dark mode (token đối ứng — cùng tên, đổi giá trị qua `[data-theme="dark"]`)
| Token | Dark |
|-------|------|
| `--bg` | `#0C1420` |
| `--surface` | `#141F2E` |
| `--surface-muted` | `#1C2A3C` |
| `--border` | `#26354A` |
| `--text` | `#E6EDF5` |
| `--text-muted` | `#9DAABA` |
| `--primary` | `#3D8FE0` |
| `--primary-soft` | `#16304D` |

### 2.6 Thang độ tin cậy (Confidence scale) — đặc thù app này
Dùng cho gauge/progress trên trang Kết quả:
- `< 50%` → `--danger` (không đủ tin cậy, không gợi ý thuốc)
- `50–74%` → `--warning` (tham khảo thận trọng)
- `≥ 75%` → `--success` (đủ tin cậy để gợi ý)

---

## 3. Typography

- **Font chữ:** `Inter` (đang dùng — giữ nguyên). Số liệu dùng `font-variant-numeric: tabular-nums`.
- **Thang cỡ chữ (type scale, 1.250 — Major Third):**

| Token | Size / Line | Weight | Dùng cho |
|-------|-------------|--------|----------|
| `--text-display` | 40 / 48 | 800 | Tiêu đề hero |
| `--text-h1` | 32 / 40 | 700 | Tiêu đề trang |
| `--text-h2` | 24 / 32 | 700 | Tiêu đề section |
| `--text-h3` | 20 / 28 | 600 | Tiêu đề card |
| `--text-body` | 16 / 24 | 400 | Văn bản chính |
| `--text-sm` | 14 / 20 | 400/500 | Label, meta |
| `--text-xs` | 12 / 16 | 600 | Eyebrow (UPPERCASE, letter-spacing .08em), caption |

---

## 4. Spacing, Radius, Elevation

**Spacing scale (base 4px):**
`--space-1: 4px` · `--space-2: 8px` · `--space-3: 12px` · `--space-4: 16px` · `--space-5: 24px` · `--space-6: 32px` · `--space-7: 48px` · `--space-8: 64px`

**Bo góc (Radius):**
`--radius-sm: 8px` (input, chip) · `--radius-md: 12px` (card) · `--radius-lg: 16px` (panel lớn) · `--radius-pill: 999px` (status pill, avatar)

**Đổ bóng (Elevation):**
- `--shadow-sm: 0 1px 2px rgba(14,27,43,.06)` — input, chip
- `--shadow-md: 0 6px 16px rgba(14,27,43,.08)` — card
- `--shadow-lg: 0 18px 40px rgba(11,95,181,.12)` — panel nổi, modal

---

## 5. Components (đặc tả để dựng trong Figma)

> Mỗi component dựng dạng **Figma Component + Variants** để tái dùng. Cột "Variants" là các thuộc tính nên tạo.

| Component | Variants | Ghi chú |
|-----------|----------|---------|
| **Button** | `type`: primary / secondary / ghost / danger · `size`: md / sm · `state`: default / hover / disabled · có/không icon | Cao 44px (md), 36px (sm); radius-sm |
| **Input / Textarea** | `state`: default / focus / error · có/không icon trái | Border `--border`, focus ring `--primary` 2px |
| **Chip (triệu chứng)** | `state`: default / selected / disabled | Pill, click để chọn; selected = `--primary-soft` + viền `--primary` |
| **Status Pill** | `tone`: success / warning / danger / neutral / secure | Nền *-soft, chữ màu semantic, có icon |
| **Card** | `kind`: default / featured / warning / dark | radius-md, shadow-md |
| **Confidence Gauge** | `level`: low / mid / high | Vòng tròn donut, màu theo §2.6, % ở giữa, tabular-nums |
| **Prediction Bar** | — | Bar ngang top-3 nhóm thuốc, label + % + thanh tỉ lệ |
| **Nav item** | `state`: default / active · `device`: sidebar / bottom | Active = nền `--primary-soft`, chữ `--primary` |
| **Avatar** | `size`: sm / md | Pill, chữ viết tắt tên |
| **Skeleton** | block / line / card | Dùng khi đang gọi model |
| **Empty state** | — | Icon + tiêu đề + mô tả, cho "Chưa có kết quả" |

---

## 6. Layout & Grid

- **Breakpoints:** mobile `< 640` · tablet `640–1024` · desktop `> 1024`.
- **Sidebar:** desktop rộng 240px (thu gọn 72px icon-rail khi hẹp); mobile ẩn → dùng `bottom-nav`.
- **Content max-width:** 1200px, padding ngang `--space-6`.
- **Grid trang chủ:** 2 cột — form bệnh án (chiếm chính) + side-stack (metric/tip). Trên tablet: xếp dọc.
- **Grid trang kết quả:** trái = summary + gauge (sticky), phải = các detail-card.

---

## 7. Trạng thái cần thiết kế (đừng quên)

- Loading (skeleton khi gọi model)
- Empty (chưa nhập / chưa có kết quả / chưa có lịch sử)
- Error (gọi model lỗi, mất mạng)
- "Không đủ tin cậy" — trạng thái đặc thù, phải khác rõ với "có kết quả"
- Focus/keyboard accessibility (viền focus rõ trên mọi control)

---

## 8. Accessibility (bắt buộc với app y tế)

- Tương phản chữ ≥ 4.5:1 (đã chọn token để đạt).
- Không dùng **chỉ màu** để truyền tin (vd độ tin cậy: thêm nhãn chữ "Cao/Trung bình/Thấp" cạnh màu).
- Mọi control có focus ring nhìn thấy; icon-button có `aria-label`.
- Target chạm tối thiểu 44×44px trên mobile.

---

## 9. Mapping sang code hiện tại

Token mới phần lớn **đổi tên** so với `styles.css` cũ (vd `--surface-lowest` → `--surface`). Khi code redesign:
1. Khai báo toàn bộ token §2–§4 trong `:root` và khối `[data-theme="dark"]`.
2. Refactor `styles.css` dùng token mới; giữ class name HTML nếu có thể để giảm rủi ro.
3. Kiểm thử UI verify từng trang khớp thiết kế trước khi merge.
