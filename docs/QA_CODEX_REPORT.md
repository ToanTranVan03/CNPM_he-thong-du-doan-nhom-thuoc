# Báo cáo QA độc lập (Codex) + fix — 2026-06-09

Codex đóng vai QA tester độc lập, tự sinh ca + input ngẫu nhiên/đối nghịch và chạy thật qua
`app.test_client()`. Phát hiện bug mà Claude và Antigravity đều bỏ sót.

## Kết quả Codex
- **Phần A** (36 ca Codex tự nghĩ): khớp 25/36 (~69%) — nhất quán với benchmark nội bộ.
- **Phần B** (20 input ngẫu nhiên/đối nghịch: rỗng, 5000 ký tự, SQL `'; DROP TABLE--`,
  `<script>`, emoji, số, trộn ngôn ngữ...): **0 crash, 0 HTTP 500, 0 exception** → guard tốt.
- **Lỗi an toàn phát hiện (đã FIX):**
  1. `Khó thở dữ dội, môi tím tái` (suy hô hấp cấp) → trước: gợi "thuốc giãn phế quản". **Bug.**
  2. `Đau ngực bóp nghẹt, lan tay trái, vã mồ hôi` (nhồi máu cơ tim) → trước: gợi "thuốc tim mạch". **Bug.**
  3. `...không ho không sốt không đau bụng... xin thuốc` (phủ định/vô nghĩa) → trước: gợi "thuốc điều trị dạ dày". **Bug.**

## Fix đã áp dụng (backend/app.py)
- Thêm `emergency_red_flag_from_notes()`: nhận **tím tái/suy hô hấp cấp** và **nhồi máu cơ tim**
  (đau ngực + lan tay/hàm/vã mồ hôi/bóp nghẹt) từ mô tả thô → ép cảnh báo cấp cứu, KHÔNG gợi thuốc.
- Mở rộng phủ định: "không đau bụng/dạ dày/thượng vị" khử cả họ `*abdominal pain*`, + "không chóng mặt", "không ngứa".

## Sau fix (xác nhận)
- 3 bug trên: đều trả 400/422 (cảnh báo/cần thêm thông tin), KHÔNG gợi thuốc. ✅
- An toàn tổng: tím tái / nhồi máu / đột quỵ / viêm màng não / co giật → đều cảnh báo. ✅
- Benchmark 120 ca: giữ **83%** (không regression). English model: 92,6% (không đụng).

## Vòng 2 (Codex gpt-5.5, reasoning xhigh) — phát hiện 10 lỗi an toàn MỚI (đã FIX)
Regression 3 fix vòng 1: PASS. Crash/500: 0. Nhưng lộ 10 ca cấp cứu/biên vẫn gợi thuốc:
- Phản vệ (ăn tôm/ong đốt/phù mạch + khó thở/tụt HA), xuất huyết tiêu hóa (nôn ra máu/phân đen + choáng),
  ngộ độc/thuốc trừ sâu, chấn thương đầu nặng, bụng ngoại khoa (bụng cứng như gỗ), thai + chảy máu/đau bụng.
- Ý định tự tử/tự hại: trước chỉ trả 400 chung chung (nên có thông điệp khủng hoảng).

### Fix vòng 2 (backend/app.py)
- Viết lại `emergency_red_flag_from_notes()` thành **cổng cấp cứu toàn diện 9 nhóm**: tự tử/tự hại
  (kèm hotline), ngộ độc/quá liều, phản vệ, xuất huyết nặng, suy hô hấp/tím tái, nhồi máu cơ tim,
  chấn thương đầu, bụng ngoại khoa, cấp cứu sản khoa.
- Đặt **cổng sớm** ngay đầu `/api/predict` (trước bước trích triệu chứng) → mọi ca cấp cứu trả 422,
  KHÔNG gợi thuốc, dù không map được triệu chứng nào.

### Sau fix vòng 2 (xác nhận)
- 12/12 ca cấp cứu/khủng hoảng → 422 (không gợi thuốc). ✅
- Benchmark 120 ca: giữ **83%** (không regression, không báo động giả). ✅

## Bài học
Fuzz/QA độc lập (input mình không tự viết) là cách hiệu quả nhất để lộ lỗi an toàn ở biên —
nên chạy định kỳ khi thêm rule mới. Reasoning effort cao (xhigh) giúp Codex nghĩ ra nhiều
kịch bản cấp cứu hiếm hơn.
