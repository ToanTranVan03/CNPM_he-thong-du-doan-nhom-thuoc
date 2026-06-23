# Thiết kế chế độ Groq chính và hàng đợi dữ liệu học

## Mục tiêu

Tạo một chế độ kiểm thử có thể bật/tắt, trong đó Groq là bộ phán đoán nhóm thuốc chính, có thể dùng tìm kiếm web để bổ sung kiến thức ngoài tập dữ liệu nội bộ. Hệ thống tiếp tục giữ các cổng cấp cứu và chống chỉ định hiện có. Mỗi phán đoán của Groq được lưu thành ứng viên dữ liệu học; chỉ mẫu đã được quản trị viên duyệt mới được xuất sang tập huấn luyện.

## Phạm vi

- Áp dụng cho endpoint dự đoán nhóm thuốc hiện tại.
- Dùng model Groq Compound có sẵn trên tài khoản để hỗ trợ tìm kiếm ngoài.
- Cho phép Groq đề xuất nhóm thuốc chưa có trong các lớp của model nội bộ.
- Không tự động kê tên thuốc, liều dùng hoặc phác đồ điều trị.
- Không tự động huấn luyện lại model trong request dự đoán.
- Không đưa mẫu chưa kiểm duyệt vào tập train chính.

## Cấu hình chế độ test

Chế độ mới được điều khiển bằng biến môi trường riêng, mặc định tắt. Khi tắt, pipeline cũ hoạt động như trước. Khi bật:

1. Cổng cấp cứu deterministic chạy trước.
2. Groq Compound nhận mô tả, triệu chứng đã chọn và danh sách ngữ cảnh an toàn.
3. Groq tìm kiếm ngoài khi cần và trả JSON có schema cố định.
4. Backend kiểm tra schema, chuẩn hóa nhóm thuốc và áp dụng cổng chống chỉ định.
5. Kết quả hợp lệ được trả cho giao diện; lỗi Groq hoặc lỗi schema chuyển về model nội bộ.
6. Một bản ghi ứng viên học được ghi bất kể kết quả được cho phép, bị chặn hay phải fallback.

Các biến dự kiến:

- `GROQ_PRIMARY_TEST_MODE=1`: bật Groq làm bộ phán đoán chính.
- `GROQ_PRIMARY_MODEL=groq/compound`: model dùng cho tìm kiếm ngoài.
- `GROQ_PRIMARY_TIMEOUT`: timeout độc lập với tầng trích xuất hiện tại.
- `GROQ_LEARNING_LOG_ENABLED=1`: bật ghi ứng viên học.
- `GROQ_LEARNING_LOG_PATH`: đường dẫn file JSONL, mặc định `data/groq_learning_candidates.jsonl`.

Khóa API tiếp tục đọc từ `LLM_API_KEY`; không sao chép khóa sang file hoặc log.

## Hợp đồng đầu ra Groq

Groq phải trả một JSON object gồm:

- `symptoms_vi`: các triệu chứng khẳng định được rút ra từ mô tả.
- `negated_vi`: các triệu chứng bị phủ định.
- `drug_group`: nhóm thuốc phù hợp nhất; có thể nằm ngoài tập lớp nội bộ.
- `rationale`: lý do ngắn, không chứa hướng dẫn liều.
- `confidence`: số từ 0 đến 1.
- `needs_clinician`: có cần bác sĩ/dược sĩ đánh giá hay không.
- `sources`: danh sách nguồn gồm tiêu đề, URL và tên miền.
- `red_flags`: các cờ đỏ theo enum an toàn hiện có.

Backend không tin trực tiếp output này. Mọi field phải được giới hạn độ dài, kiểm tra kiểu, loại bỏ HTML và chỉ chấp nhận URL HTTP(S). Prompt yêu cầu ưu tiên Bộ Y tế, WHO, NHS, CDC và tài liệu dược chính thống. Nguồn ngoài là bằng chứng hỗ trợ, không được phép vô hiệu hóa cổng an toàn nội bộ.

## Cổng an toàn

### Cấp cứu

Cổng cấp cứu chạy trước Groq. Nếu phát hiện cờ đỏ, endpoint trả `422` và không gọi Groq để xin nhóm thuốc. Các nhóm hiện có như tự hại, ngộ độc/quá liều, phản vệ, suy hô hấp, hội chứng vành cấp, đột quỵ, co giật, xuất huyết, cấp cứu sản khoa và các tình trạng cấp khác được giữ nguyên.

### Chống chỉ định

Sau khi Groq chọn nhóm, kết quả đi qua `context_safety.safety_overrides` và các rule rủi ro hiện có. Dị ứng thuốc, NSAID trong bối cảnh chống chỉ định, nhóm giảm đau ở người có bệnh gan, trẻ sơ sinh và các cổng kê đơn/chuyên khoa tiếp tục được phép thay thế kết quả bằng cảnh báo hoặc yêu cầu đi khám.

Groq không được tự gỡ chặn. Nếu Groq nhận ra thêm cờ đỏ, backend có thể chặn bổ sung sau khi đã chứng thực tín hiệu trong mô tả.

## Hàng đợi dữ liệu học

File `data/groq_learning_candidates.jsonl` là append-only; mỗi dòng là một JSON object độc lập. Schema dự kiến:

- `id`: mã định danh ngẫu nhiên.
- `created_at`: UTC ISO-8601.
- `input_hash`: hash ổn định để khử trùng.
- `notes_redacted`: mô tả đã loại email, số điện thoại và định danh phổ biến.
- `selected_symptoms`: triệu chứng người dùng chọn.
- `extracted_symptoms_vi`: triệu chứng Groq trích xuất.
- `negated_vi`: triệu chứng phủ định.
- `proposed_drug_group`: nhóm Groq đề xuất.
- `rationale`: lý do ngắn.
- `confidence`: 0..1.
- `sources`: nguồn tham khảo đã validate.
- `safety_disposition`: `allowed`, `blocked_emergency`, `blocked_contraindication`, `needs_clinician` hoặc `fallback`.
- `model`: model Groq đã dùng.
- `prompt_version`: phiên bản prompt/schema.
- `review_status`: mặc định `pending`; chỉ nhận `pending`, `approved`, `rejected`.
- `reviewed_at`, `reviewed_by`, `review_note`: thông tin kiểm duyệt.

File không lưu token phiên, email tài khoản, API key hoặc dữ liệu xác thực. Ghi file dùng khóa tiến trình và một lần append để tránh dòng JSON bị xen kẽ khi có request đồng thời. Lỗi ghi log không được làm hỏng request dự đoán nhưng phải có log kỹ thuật không chứa dữ liệu bệnh án.

## Quy trình duyệt và xuất dữ liệu train

Một script riêng đọc JSONL, kiểm tra schema và chỉ xuất bản ghi `approved`. Dữ liệu xuất tương thích với pipeline hiện tại:

- `trieu_chung`: mô tả/triệu chứng đã chuẩn hóa.
- `nhom_thuoc`: nhãn đã được duyệt.
- `source`: `groq_reviewed:<model>`.

Script phải khử trùng theo `input_hash`, từ chối mẫu thiếu nguồn hoặc bị chặn an toàn, và không sửa trực tiếp tập train gốc. Đầu ra là một CSV mới để người quản trị chủ động ghép qua pipeline build/train hiện có.

Việc đổi trạng thái duyệt có thể thực hiện bằng script CLI trước. UI quản trị cho duyệt hàng loạt là phần mở rộng, không bắt buộc cho chế độ test đầu tiên.

## Xử lý lỗi và fallback

- Timeout, HTTP lỗi, JSON sai schema hoặc không có nhóm thuốc: dùng model nội bộ.
- Groq trả nhóm ngoài dữ liệu: vẫn có thể hiển thị nếu hợp lệ và không bị chặn; phần mô tả/hoạt chất nội bộ có thể để trống.
- Không có nguồn khi Groq tuyên bố đã dùng web: hạ độ tin cậy và yêu cầu bác sĩ/dược sĩ xác nhận.
- File ứng viên bị lỗi: request vẫn trả kết quả, đồng thời ghi cảnh báo kỹ thuật an toàn.
- Chế độ test được tắt bằng một biến môi trường và khởi động lại server, không cần rollback code.

## Kiểm thử chấp nhận

1. Ca thông thường trong dữ liệu: Groq trả nhóm hợp lệ và lưu một ứng viên `pending`.
2. Ca ngoài dữ liệu: Groq có thể trả nhóm mới kèm nguồn; frontend không lỗi.
3. Ca cấp cứu: bị chặn trước khi phân loại nhóm thuốc.
4. Ca chống chỉ định: Groq có thể chọn nhóm nhưng backend trả cảnh báo `422`.
5. Groq timeout/HTTP lỗi/JSON hỏng: model nội bộ tiếp quản.
6. Dữ liệu nhạy cảm phổ biến được loại khỏi `notes_redacted`.
7. Hai request giống nhau được nhận diện bằng `input_hash` khi xuất train.
8. Script chỉ xuất mẫu `approved`; không xuất `pending`, `rejected` hoặc mẫu bị chặn.
9. Tắt chế độ test khôi phục hành vi pipeline cũ.
10. Bộ regression hiện tại tiếp tục chạy qua khi chế độ mới tắt.

## Không nằm trong phạm vi

- Tự động retrain/deploy model sau mỗi request.
- Tin hoàn toàn vào một nguồn web không xác thực.
- Chẩn đoán chắc chắn, kê đơn, liều dùng hoặc thay thế bác sĩ.
- Tự động duyệt nhãn do chính Groq tạo ra.
