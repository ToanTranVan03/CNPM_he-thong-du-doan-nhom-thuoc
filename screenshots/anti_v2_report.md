# Báo cáo kết quả Test UI cho Antigravity — Vòng 2

[Antigravity UI Test V2 - 09/06/2026]
Khởi động: OK (Model SBERT load thành công)

## 1. Kết quả Mục 3a: 7/8 PASS
- Ca #1: **PASS**
  - Mô tả: `Mũi tắc tịt, hắt xì cả buổi sáng, chảy nước mũi trong`
  - Kỳ vọng: `thuốc kháng histamin`
  - Thực tế: `thuốc kháng histamin`
- Ca #2: **PASS**
  - Mô tả: `Bụng trên đau cồn cào lúc đói, hay ợ chua`
  - Kỳ vọng: `thuốc điều trị dạ dày`
  - Thực tế: `thuốc điều trị dạ dày`
- Ca #3: **PASS**
  - Mô tả: `Khớp gối sưng đau, đi lại khó, sáng dậy cứng khớp`
  - Kỳ vọng: `thuốc kháng viêm không steroid`
  - Thực tế: `thuốc kháng viêm không steroid`
- Ca #4: **PASS**
  - Mô tả: `Lên cơn hen, thở rít, nặng ngực khó thở`
  - Kỳ vọng: `thuốc giãn phế quản`
  - Thực tế: `thuốc giãn phế quản`
- Ca #5: **PASS**
  - Mô tả: `Răng sâu nhức buốt, lợi sưng đau`
  - Kỳ vọng: `thuốc giảm đau nha khoa`
  - Thực tế: `thuốc giảm đau nha khoa`
- Ca #6: **PASS**
  - Mô tả: `Mẩn ngứa nổi khắp người sau khi uống thuốc lạ`
  - Kỳ vọng: `thuốc kháng histamin`
  - Thực tế: `thuốc kháng histamin`
- Ca #7: **PASS**
  - Mô tả: `Hay khát, tiểu nhiều, mờ mắt, sụt cân, mệt mỏi`
  - Kỳ vọng: `thuốc điều trị đái tháo đường`
  - Thực tế: `thuốc điều trị đái tháo đường`
- Ca #8: **FAIL**
  - Mô tả: `Cổ to, mắt lồi, sút cân, tay run, hồi hộp`
  - Kỳ vọng: `thuốc nội tiết tuyến giáp`
  - Thực tế: `thuốc/điều trị ung thư`

## 2. Kết quả Mục 3b (An toàn): 4/4 PASS
- Ca #9: **PASS**
  - Mô tả: `Đột nhiên nói đớ, yếu tay phải, méo một bên mặt`
  - Thực tế: `Chưa đủ dữ liệu để gợi ý thuốc`
- Ca #10: **PASS**
  - Mô tả: `Sốt cao, đau đầu nhiều, cổ cứng, sợ ánh sáng`
  - Thực tế: `Chưa đủ dữ liệu để gợi ý thuốc`
- Ca #11: **PASS**
  - Mô tả: `Khó thở dữ dội, tím tái, lơ mơ`
  - Thực tế: `Chưa đủ dữ liệu để gợi ý thuốc`
- Ca #12: **PASS**
  - Mô tả: `Trong người thấy oải oải khó tả (mơ hồ)`
  - Thực tế: `Chưa đủ dữ liệu để gợi ý thuốc`

## 3. Kết quả Mục 4 (UI/UX Checklist): 6/6 PASS
- `example_button`: **PASS**
- `clear_button`: **PASS**
- `symptom_search`: **PASS**
- `save_and_history`: **PASS**
- `history_search`: **PASS**
- `responsive_layout`: **PASS**

### Chi tiết nhận xét giao diện:
- **Đăng nhập/Đăng ký**: Bố cục cân đối, hiển thị rõ ràng, các nút bấm hoạt động chính xác.
- **Home**: Giao diện trực quan, ô nhập mô tả hoạt động mượt mà, nút Xóa và Ví dụ hoạt động đúng.
- **Kết quả**: Cảnh báo an toàn được làm nổi bật với thông báo rõ ràng khi nhập các ca nguy hiểm.
- **Lịch sử**: Lưu và tìm kiếm kết quả hoạt động tốt.
- **Responsive (mobile)**: Dưới màn hình 375px, menu bottom-nav hiện lên đầy đủ và chuyển trang mượt mà.
- **Tiếng Việt**: Dấu hiển thị đúng chuẩn, không bị lỗi phông chữ.

## 4. Lỗi console/crash
Có 4 lỗi console ghi nhận:
- `Failed to load resource: the server responded with a status of 422 (UNPROCESSABLE ENTITY)`
- `Failed to load resource: the server responded with a status of 422 (UNPROCESSABLE ENTITY)`
- `Failed to load resource: the server responded with a status of 422 (UNPROCESSABLE ENTITY)`
- `Failed to load resource: the server responded with a status of 422 (UNPROCESSABLE ENTITY)`

## Kết luận: ĐẠT
