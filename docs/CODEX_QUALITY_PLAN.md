# Kế hoạch nâng chất lượng và an toàn chẩn đoán PharmaPredict

> **Dành cho agent triển khai:** thực hiện tuần tự P0 -> P4. Không chuyển giai đoạn khi gate an toàn của giai đoạn trước chưa đạt. Giữ API contract hiện có và ưu tiên trả lời thận trọng hơn là cố đưa ra một nhóm thuốc.

**Mục tiêu:** Ngăn mọi ca có cờ đỏ nhận gợi ý thuốc, trình bày đúng mức độ chắc chắn, giảm nhãn bệnh vô nghĩa và đo chất lượng bằng bộ ca độc lập thay vì bộ template vòng tròn.

**Kiến trúc đề xuất:** Tách luồng `/api/predict` thành bốn quyết định tuần tự: kiểm tra input -> phân luồng an toàn -> đánh giá đủ dữ liệu/độ tin cậy -> mới cho phép gợi ý nhóm thuốc. Rule và model phải đi qua cùng một policy an toàn; phần trình bày chỉ phản ánh quyết định đã được policy cho phép.

**Công nghệ:** Python, Flask test client, scikit-learn/joblib hiện có, HTML/CSS/JavaScript thuần, chạy local bằng `python backend/app.py`; không thêm framework hoặc dịch vụ mạng bắt buộc.

---

## Phạm vi và ràng buộc khóa

- Giữ các field mà frontend đang dùng: `case_summary{diagnosis,medication_name,drug_group}`, `confidence`, `score_type`, `display_title`, `top_predictions`, `matched_symptoms_vi`, `needs_more_input`, `warning`.
- Giữ các status của `/api/predict`: `200` cho kết quả được phép hiển thị, `400` cho input không hợp lệ/không nhận diện được, `422` cho ca bị chặn vì an toàn hoặc chưa đủ tin cậy.
- Không hiển thị rule như xác suất 100%; `confidence=null` phải được hiểu là “không có xác suất đã hiệu chỉnh”.
- Không dùng độ chính xác nội bộ `95.3%` trong `models/metadata.json` như bằng chứng chất lượng lâm sàng.
- Không hứa “chính xác như bác sĩ”, không gọi kết quả là đơn thuốc, không đưa liều dùng.
- Không dùng `scripts/stress_test_user_cases.py` làm chỉ số chất lượng chính; script này chỉ còn vai trò smoke/regression.

## Baseline đã xác nhận ngày 2026-06-15

- Chạy `scripts/independent_probe.py` ở chế độ offline cho thấy **2/3 red flag vẫn nhận nhóm thuốc**: ho 3 tuần kèm sụt cân/ra mồ hôi đêm và đau dữ dội hố chậu phải.
- Ca sốt cao co giật đã bị chặn `422`, nhưng `case_summary.diagnosis` vẫn là `hypoglycemia`, không phản ánh lý do chặn.
- Rule cơ-xương và táo bón trả nhóm tạm hợp lý nhưng gắn nhãn bệnh sai như `spinal stenosis`, `hemorrhoids`.
- Ca mất ngủ/lo âu vẫn nhận `thuốc tim mạch/huyết áp`.
- Chạy probe mặc định có thể cố tải SBERT từ Hugging Face; trên Windows còn có thể lỗi encoding console. Đây là lỗi tái lập local cần xử lý trong P3.

## Thang rủi ro

- **Thấp:** thay đổi test/report hoặc copy, ít ảnh hưởng quyết định.
- **Trung bình:** thay đổi presentation hoặc ngưỡng, có thể tăng số ca `422`.
- **Cao:** thay đổi rule, trích triệu chứng hoặc response builder, có thể tạo false positive/false negative.
- **Rất cao:** thay đổi thứ tự triage, model hoặc dữ liệu train; lỗi có thể làm red flag nhận thuốc.

---

## P0 - An toàn: chặn nguy hiểm trước mọi gợi ý

**Gate P0:** Chỉ chuyển sang P1 khi toàn bộ ca red flag trong probe bị chặn, không có tên thuốc/nhóm thuốc/hoạt chất, và API safety response đủ contract.

- [ ] **P0.1 Tách bộ phân luồng an toàn khỏi rule chọn thuốc** — **File/vùng code:** `backend/app.py:1835-1917` (`emergency_red_flag_from_notes`), `1791-1811` (`has_neuro_danger_signs`), `2042-2085` (`llm_safety_red_flag_message`), `2736-2877` (`predict`). **Mô tả:** Tạo một kết quả triage nội bộ có tối thiểu `severity`, `reason`, `action`; chạy cổng raw-text trước trích triệu chứng và cổng có `active_symptoms` ngay sau trích triệu chứng, cả hai đều trước model/rule chọn nhóm thuốc. Phân biệt “cấp cứu ngay” với “cần khám sớm/tầm soát”, nhưng cả hai đều không được gợi ý thuốc. **Tiêu chí nghiệm thu:** 100% ca có `safety=red_flag` trong `independent_probe` trả `422`, `needs_more_input=true`, `top_predictions=[]`; không ca nào đi tiếp tới `rule_group` hoặc model output dùng cho presentation. **Rủi ro:** **Rất cao** - đặt sai thứ tự có thể bỏ sót cấp cứu hoặc chặn quá nhiều ca lành tính.

- [ ] **P0.2 Bổ sung ba cụm cờ đỏ đang bị bỏ sót** — **File/vùng code:** `backend/app.py:1835-1917`, vùng keyword `334-542`, vùng helper phủ định `1490-1526`. **Mô tả:** Thêm nhận diện có tổ hợp, không dựa vào một từ đơn: ho kéo dài khoảng 3 tuần kèm sụt cân/ra mồ hôi đêm/ho ra máu; đau bụng khu trú dữ dội vùng hố chậu phải kèm sốt hoặc buồn nôn/nôn; sốt cao kèm co giật, đặc biệt ở trẻ. Áp dụng phủ định để “không sụt cân”, “không co giật” không kích hoạt sai. **Tiêu chí nghiệm thu:** Tối thiểu 12 biến thể red flag của ba cụm trên đều bị chặn; tối thiểu 8 ca đối chứng có phủ định/triệu chứng nhẹ không bị gắn cấp cứu sai; **0 red flag bị kê thuốc**. **Rủi ro:** **Rất cao** - pattern quá rộng gây báo động giả, quá hẹp tiếp tục bỏ sót.

- [ ] **P0.3 Chuẩn hóa safety response và giữ API contract** — **File/vùng code:** `backend/app.py:2555-2571` (`case_summary`), `2736-2812` (hai nhánh `422`), `2969-2994` (nhánh chưa đủ dữ liệu); `frontend/script.js:265-270`, `547-575`, `578-600`. **Mô tả:** Dùng một response builder cho mọi safety/insufficient response. Với safety block, vẫn trả đủ `case_summary`, `confidence`, `score_type`, `display_title`, `top_predictions`, `matched_symptoms_vi`, `needs_more_input`, `warning`; `medication_name` và `drug_group` phải là thông điệp “Không gợi ý thuốc - cần đi khám”. **Tiêu chí nghiệm thu:** Contract probe có fixture cho `200`, `400`, `422`; status thực tế đúng kỳ vọng 100%; mọi response `200/422` có đủ field bắt buộc và đúng type; `422` safety có `confidence=null`, `top_predictions=[]`, không có hoạt chất/tên thuốc. **Rủi ro:** **Cao** - thay schema hoặc type có thể làm `frontend/script.js` lỗi render.

- [ ] **P0.4 Buộc mọi rule và model đi qua một chốt “được phép gợi ý thuốc”** — **File/vùng code:** `backend/app.py:2850-2877` (`rule_group`), `2880-2968` (`quality_reasons`), `2996-3090` (response thành công). **Mô tả:** Không dùng `score_type=="rule"` như vé bỏ qua mọi kiểm tra. Tạo quyết định cuối `can_suggest_drug` chỉ đúng khi không có safety flag, không có chống chỉ định chặn và đủ bằng chứng theo policy. **Tiêu chí nghiệm thu:** Với toàn bộ red flag, `case_summary.drug_group` và `case_summary.medication_name` không chứa nhóm/tên thuốc; `representative_active_ingredients` rỗng hoặc không xuất hiện; `medications` chỉ chứa hướng đi khám/chăm sóc không kê thuốc; số vi phạm bằng 0. **Rủi ro:** **Rất cao** - lỗi boolean hoặc thứ tự có thể làm rule vượt cổng an toàn.

- [ ] **P0.5 Loại nhãn bệnh model/dataset khỏi safety response** — **File/vùng code:** `backend/app.py:2443-2518` (`heuristic_diagnosis`, `dataset_diagnosis`), `2555-2571` (`case_summary`), các return `422` trong `predict`. **Mô tả:** Khi bị chặn an toàn, `diagnosis` phải mô tả đúng lý do phân luồng như “Cờ đỏ hô hấp cần khám sớm” hoặc “Sốt cao kèm co giật - cần cấp cứu”, không được dùng nhãn bệnh suy ra từ dataset. **Tiêu chí nghiệm thu:** Các ca ho kéo dài/sụt cân, đau hố chậu phải và sốt/co giật có diagnosis khớp đúng nhóm cờ đỏ; **0** safety response chứa `spinal stenosis`, `hemorrhoids`, `hypoglycemia`, `Osteoarthristis` hoặc raw disease tiếng Anh khác. **Rủi ro:** **Cao** - copy sai mức khẩn cấp có thể khiến người dùng đánh giá thấp tình trạng.

- [ ] **P0.6 Thêm ca đối chứng để kiểm soát báo động giả** — **File/vùng code:** `scripts/independent_probe.py` và data case độc lập sẽ tách ở P3. **Mô tả:** Thêm near-miss như ho 2 ngày không sụt cân, đau bụng nhẹ lan tỏa không sốt, tiền sử co giật nhưng hiện không co giật, câu có phủ định rõ. **Tiêu chí nghiệm thu:** Tối thiểu 8/8 near-miss không bị trả thông điệp “gọi 115/cấp cứu” sai; ca còn thiếu dữ liệu có thể trả `422 needs_more_input`, nhưng không được gắn sai lý do red flag. **Rủi ro:** **Trung bình** - ép false-positive bằng 0 tuyệt đối có thể làm giảm độ nhạy; chỉ áp cho bộ đối chứng đã gắn nhãn rõ.

- [ ] **P0.7 Tạo gate an toàn chạy độc lập trước mọi merge** — **File/vùng code:** `scripts/independent_probe.py`; có thể thêm `scripts/score_independent_probe.py` ở P3. **Mô tả:** Probe phải trả exit code khác 0 nếu có red flag nhận thuốc hoặc safety response sai contract. **Tiêu chí nghiệm thu:** Cố tình làm một red flag trả `200` khiến probe fail; bản đúng trả exit code `0` và in rõ `red_flag_drug_count=0`. **Rủi ro:** **Thấp** - test sai định nghĩa `gave_drug` có thể tạo cảm giác an toàn giả.

---

## P1 - Trình bày trung thực: không biến heuristic thành sự chắc chắn

**Gate P1:** Rule không còn hiển thị như 100%; trạng thái an toàn/không chắc chắn rõ hơn kết quả; không có copy khẳng định quá mức.

- [ ] **P1.1 Sửa semantics confidence của rule** — **File/vùng code:** `frontend/script.js:426-472`, `506-517`; `backend/app.py:2872-2877`, `3046-3090`. **Mô tả:** Giữ `confidence=null` cho rule; thanh confidence không được rộng 100%. Hiển thị “Quy tắc sàng lọc/heuristic - không phải xác suất” thay cho “Theo rule an toàn” và không dùng mức “Tin cậy cao”. **Tiêu chí nghiệm thu:** 100% fixture `score_type="rule"` hiển thị `N/A` hoặc nhãn trung tính, progress không vượt 0%/không dùng gauge phần trăm, DOM không chứa chuỗi `100%` hoặc `Tin cậy cao` cho rule. **Rủi ro:** **Trung bình** - thay render confidence có thể ảnh hưởng layout và các trạng thái model.

- [ ] **P1.2 Hiển thị safety/insufficient như trạng thái hành động, không phải kết quả gần nhất** — **File/vùng code:** `frontend/script.js:445-575`. **Mô tả:** Với `422`, ưu tiên `display_title`, `warning`, hành động đi khám/bổ sung thông tin; không hiển thị “khả năng gần nhất”, top prediction hoặc tên nhóm thuốc bị chặn. **Tiêu chí nghiệm thu:** 100% fixture safety và insufficient có `top-predictions` rỗng; không có tên thuốc/nhóm thuốc dự đoán trong title/note/list; cảnh báo và hành động xuất hiện ở vùng nhìn thấy. **Rủi ro:** **Cao** - phân nhánh sai có thể che cảnh báo hoặc vẫn lộ dự đoán.

- [ ] **P1.3 Đặt chính sách hiển thị nhãn bệnh theo bằng chứng** — **File/vùng code:** `backend/app.py:2443-2518`, `2555-2571`, `1622-1632`; `frontend/script.js:265-270`, `473-492`. **Mô tả:** Chỉ hiển thị nhãn bệnh cụ thể khi có heuristic đặc hiệu đã được kiểm thử; nếu bằng chứng thấp hoặc chỉ có dataset overlap, dùng nhãn hội chứng trung tính như “Đau cơ-xương sau vận động” hoặc “Táo bón - chưa xác định nguyên nhân”. **Tiêu chí nghiệm thu:** Trên probe độc lập, **0** ca có diagnosis mâu thuẫn với mô tả; **0** raw disease tiếng Anh; 100% ca không đủ bằng chứng dùng nhãn trung tính/cần bổ sung thông tin. **Rủi ro:** **Cao** - có thể giảm độ chi tiết hiển thị, nhưng đây là trade-off an toàn chủ đích.

- [ ] **P1.4 Đồng bộ title, summary và warning** — **File/vùng code:** `backend/app.py:1628-1632`, `2555-2571`, các response trong `predict`; `frontend/script.js:265-270`, `473-504`, `547-575`. **Mô tả:** Không để `display_title` nói “Nhóm thuốc gợi ý” trong khi `case_summary` nói chưa đủ dữ liệu; safety title, summary và warning phải cùng mức khẩn cấp. **Tiêu chí nghiệm thu:** Contract scorer kiểm tra 100% response không có cặp trạng thái mâu thuẫn; nếu `needs_more_input=true` thì `case_summary.medication_name/drug_group` không chứa gợi ý thuốc. **Rủi ro:** **Trung bình** - copy không đồng bộ làm người dùng hiểu sai dù backend đã chặn đúng.

- [ ] **P1.5 Chuẩn hóa ngôn ngữ giới hạn** — **File/vùng code:** `backend/app.py:181-316`, `1008-1209`, `1672-1703`, `2574-2586`; `frontend/script.js:479-504`, `563-571`. **Mô tả:** Dùng nhất quán “gợi ý tham khảo”, “không phải chẩn đoán/đơn thuốc”, “cần bác sĩ hoặc dược sĩ xác nhận”; bỏ câu khiến rule nghe như kết luận lâm sàng chắc chắn. **Tiêu chí nghiệm thu:** Các chuỗi user-facing trong `backend/app.py` và `frontend/script.js` không có claim “chính xác như bác sĩ”, “chắc chắn”, “khẳng định bệnh”, “đơn thuốc của bạn”; mọi result được phép gợi ý thuốc vẫn có `warning` không rỗng. **Rủi ro:** **Thấp** - chủ yếu là copy nhưng có tác động trực tiếp đến cách hiểu.

- [ ] **P1.6 Regression UI contract bằng fixture local** — **File/vùng code:** `frontend/script.js`, có thể thêm fixture vào `scripts/independent_probe.py` hoặc script smoke JS hiện có. **Mô tả:** Kiểm tra tối thiểu sáu trạng thái: model `200`, rule `200`, insufficient `422`, urgent safety `422`, emergency `422`, invalid `400`. **Tiêu chí nghiệm thu:** Sáu fixture render không lỗi JavaScript; các ID hiện có vẫn được dùng; không response nào gây `undefined%`, thanh 100% giả hoặc exception console. **Rủi ro:** **Trung bình** - fixture không sát response thật sẽ bỏ sót regression.

---

## P2 - Độ tin cậy nhãn bệnh và quyết định abstain

**Gate P2:** Nhãn bệnh chỉ xuất hiện khi có bằng chứng; rule và model cùng chịu policy độ tin cậy; các ca mơ hồ chủ động abstain.

- [ ] **P2.1 Tách “nhãn mô tả ca” khỏi “disease label từ dataset”** — **File/vùng code:** `backend/app.py:2434-2518`, `2555-2571`. **Mô tả:** `case_summary.diagnosis` trở thành nhãn mô tả đã kiểm soát, ưu tiên syndrome/triage; `dataset_diagnosis` không được tự động quyết định presentation chỉ vì overlap triệu chứng. **Tiêu chí nghiệm thu:** 100% ca probe có `diagnosis` tiếng Việt; **0** nhãn disease không có trong allowlist/policy; các ca đau cơ sau vận động và táo bón không còn nhãn `spinal stenosis`/`hemorrhoids`. **Rủi ro:** **Cao** - thay đổi ý nghĩa field nhưng vẫn phải giữ tên field để không vỡ frontend.

- [ ] **P2.2 Đặt ngưỡng riêng cho nhãn bệnh** — **File/vùng code:** `backend/app.py:2494-2518` (`dataset_diagnosis`), vùng constants `69-83`. **Mô tả:** Nếu vẫn dùng dataset label, yêu cầu tối thiểu số triệu chứng, precision/coverage và độ nhất quán với nhóm thuốc; dưới ngưỡng phải trả nhãn trung tính. Không tái sử dụng trực tiếp confidence nhóm thuốc làm confidence nhãn bệnh. **Tiêu chí nghiệm thu:** Trên tập nhãn bệnh độc lập, 100% ca `generic_required` bị ẩn/thay bằng nhãn trung tính; số nhãn bệnh mâu thuẫn bằng 0; không tăng số red flag nhận thuốc. **Rủi ro:** **Cao** - ngưỡng thấp tạo nhãn sai, ngưỡng cao làm phần lớn nhãn bị ẩn.

- [ ] **P2.3 Phân tầng rule theo mức rủi ro và độ đặc hiệu** — **File/vùng code:** `backend/app.py:1706-2210`, `2850-2877`. **Mô tả:** Mỗi rule khai báo mức `low_risk_symptomatic`, `needs_confirmation`, hoặc `high_risk_no_autosuggest`; rule thuốc tim mạch, tâm thần, kháng sinh, kháng virus, ung thư/miễn dịch không được coi tương đương rule bù dịch/chăm sóc triệu chứng. **Tiêu chí nghiệm thu:** **0** rule high-risk kích hoạt từ một triệu chứng chung; mọi output high-risk cần tổ hợp đặc hiệu đã gắn nhãn hoặc bị chuyển `422`; probe không còn ca mất ngủ/lo âu -> tim mạch. **Rủi ro:** **Rất cao** - phân tầng sai có thể vừa bỏ sót vừa gợi ý nhóm nguy hiểm.

- [ ] **P2.4 Áp dụng evidence policy chung cho rule và model** — **File/vùng code:** `backend/app.py:2880-2968`. **Mô tả:** Tạo policy dùng nguồn dự đoán, số triệu chứng, top-gap, confidence, mức rủi ro nhóm, unsupported symptoms và contradiction để quyết định `allow/abstain/safety_block`; bỏ các điều kiện `score_type != "rule"` không có lý do an toàn. **Tiêu chí nghiệm thu:** 100% rule/model response có decision path xác định; test unit/fixture bao phủ đủ ba quyết định; rule mơ hồ trả `422` thay vì `200`; red flag vẫn bằng 0 thuốc. **Rủi ro:** **Rất cao** - đây là trung tâm quyết định của toàn API.

- [ ] **P2.5 Kiểm tra tính nhất quán giữa diagnosis và drug group** — **File/vùng code:** `backend/app.py:2443-2571`, `2969-3090`; scorer ở `scripts/`. **Mô tả:** Nếu diagnosis và drug group thuộc hai hướng mâu thuẫn, không cố hiển thị cả hai; ưu tiên abstain hoặc dùng nhãn mô tả triệu chứng. **Tiêu chí nghiệm thu:** Scorer có rule contradiction; **0** response trong bộ độc lập có các cặp như “viêm hô hấp trên” + “thuốc chống nôn” cho đau hố chậu phải, hoặc nhãn bệnh cột sống cho đau cơ sau vận động. **Rủi ro:** **Cao** - mapping contradiction cần được duy trì có kiểm soát, tránh danh sách ad hoc quá lớn.

- [ ] **P2.6 Bảo toàn case summary khi abstain** — **File/vùng code:** `backend/app.py:2521-2571`, `2969-2994`; `frontend/script.js:265-270`. **Mô tả:** Khi abstain, vẫn trả mô tả ca và triệu chứng đã nhận diện, nhưng ba field summary không được tạo cảm giác đã kê thuốc/chẩn đoán chắc chắn. **Tiêu chí nghiệm thu:** 100% `needs_more_input=true` có `medication_name` và `drug_group` bằng thông điệp không gợi ý thuốc; `diagnosis` là nhãn trung tính; không field bắt buộc nào rỗng. **Rủi ro:** **Trung bình** - placeholder không nhất quán có thể bị scorer hiểu là thuốc thật.

---

## P3 - Bộ QA độc lập, tái lập và có số liệu thật

**Gate P3:** Có ít nhất 60 ca độc lập, trong đó tối thiểu 40 ca holdout khóa trước P4; scorer chạy một lệnh, offline, trả exit code theo gate.

- [ ] **P3.1 Tách dữ liệu ca khỏi code probe** — **File/vùng code:** sửa `scripts/independent_probe.py`; tạo `scripts/independent_cases.json`. **Mô tả:** Mỗi ca có `id`, mô tả tự nhiên, `expected_action` (`suggest/abstain/urgent/emergency`), nhóm chấp nhận, cờ an toàn, policy diagnosis và ghi chú lý do. Không lấy câu trực tiếp từ template/rule trong `app.py`. **Tiêu chí nghiệm thu:** File có tối thiểu 60 ca hợp lệ; schema validation pass 100%; không trùng normalized text; mỗi ca có nhãn kỳ vọng và lý do. **Rủi ro:** **Trung bình** - nhãn kỳ vọng sai sẽ làm toàn bộ metric sai.

- [ ] **P3.2 Thiết kế phân bố ca chống vòng tròn** — **File/vùng code:** `scripts/independent_cases.json`, tài liệu report trong `docs/`. **Mô tả:** Tối thiểu 15 red flag/urgent, 25 ca có nhóm thuốc/chăm sóc hợp lý thuộc ít nhất 8 nhóm, 10 ca mơ hồ cần abstain, 10 ca phủ định/ngoài tập train/near-miss; có paraphrase, lỗi gõ nhẹ, thời gian, vị trí, tuổi. **Tiêu chí nghiệm thu:** Scorer xác nhận đủ quota từng lớp; không lớp nào chiếm quá 35% tổng bộ; có ít nhất 10 ca không khớp bất kỳ template stress cũ sau normalize. **Rủi ro:** **Trung bình** - phân bố không đại diện có thể tối ưu sai hướng.

- [ ] **P3.3 Khóa calibration và holdout trước P4** — **File/vùng code:** `scripts/independent_cases.json`, `scripts/independent_probe.py`. **Mô tả:** Gắn 20 ca `split=calibration` để chỉnh ngưỡng và tối thiểu 40 ca `split=holdout` để nghiệm thu; lưu checksum/version. Không sửa expected của holdout để làm metric đẹp hơn. **Tiêu chí nghiệm thu:** Report in version và SHA-256; P4 chỉ đọc kết quả holdout ở gate cuối; mọi thay đổi nội dung holdout làm checksum đổi và phải được review như thay test spec. **Rủi ro:** **Cao** - xem và tune trực tiếp trên holdout sẽ tái tạo đúng lỗi vòng tròn hiện tại.

- [ ] **P3.4 Tạo scorer định lượng** — **File/vùng code:** tạo `scripts/score_independent_probe.py`; gọi từ `scripts/independent_probe.py`. **Mô tả:** Tính tối thiểu: `red_flag_drug_count`, safety recall, đúng nhóm trên toàn bộ ca eligible, precision khi có gợi ý, coverage, abstain accuracy, high-risk false positive, diagnosis contradiction, contract failure. Abstain trên ca eligible phải tính là chưa đúng nhóm để tránh “an toàn giả” bằng cách chặn tất cả. **Tiêu chí nghiệm thu:** Scorer xuất JSON và Markdown; metric được kiểm tra bằng fixture nhỏ có kết quả tính tay; sai một red flag hoặc contract làm exit code khác 0. **Rủi ro:** **Cao** - công thức metric sai có thể khuyến khích hành vi không mong muốn.

- [ ] **P3.5 Làm probe chạy offline và ổn định trên Windows** — **File/vùng code:** `scripts/independent_probe.py`, vùng khởi tạo semantic trong `backend/app.py:837-855` nếu cần. **Mô tả:** Probe mặc định không tải model qua mạng; cấu hình encoding UTF-8 trước khi import app hoặc xuất report bằng file UTF-8; semantic chỉ được bật khi model đã có local và được yêu cầu rõ. **Tiêu chí nghiệm thu:** `python scripts/independent_probe.py` chạy thành công trên máy local không mạng, không retry Hugging Face, không `UnicodeEncodeError`, hai lần liên tiếp cho cùng metric/checksum. **Rủi ro:** **Trung bình** - tắt semantic trong QA có thể khác runtime; report phải ghi rõ mode.

- [ ] **P3.6 Biến API contract thành kiểm thử bắt buộc** — **File/vùng code:** `scripts/score_independent_probe.py`, `backend/app.py` response branches, `frontend/script.js` contract. **Mô tả:** Kiểm tra type và sự hiện diện field bắt buộc cho response `200/422`, đồng thời xác nhận input invalid vẫn là `400` và không có `500`. **Tiêu chí nghiệm thu:** Tối thiểu một fixture cho từng status `200/400/422`; `contract_failure_count=0`; xóa thử một field bắt buộc làm scorer fail. **Rủi ro:** **Thấp** - contract test quá cứng với field tùy chọn có thể gây false failure; chỉ khóa field frontend đang dùng.

- [ ] **P3.7 Hạ `stress_test_user_cases.py` về smoke/regression** — **File/vùng code:** `scripts/stress_test_user_cases.py`, `docs/stress_test_500_summary.json`, report chất lượng mới. **Mô tả:** Giữ 500 ca để phát hiện crash/status/schema regression, nhưng report phải ghi rõ là template-derived và không dùng tỷ lệ 91.8% làm headline chất lượng. Sửa check red flag để “có warning” không được coi là đủ nếu vẫn có thuốc. **Tiêu chí nghiệm thu:** Report stress tách riêng khỏi independent score; red flag stress chỉ pass khi không có thuốc; tài liệu không dùng `passed/500` như accuracy chẩn đoán. **Rủi ro:** **Thấp** - thay ý nghĩa report có thể làm so sánh lịch sử khó hơn.

- [ ] **P3.8 Xuất báo cáo trước/sau có thể audit** — **File/vùng code:** tạo `docs/quality_independent_report.json` và `docs/quality_independent_report.md` khi triển khai; scorer trong `scripts/`. **Mô tả:** Báo cáo lưu commit/model metadata, mode semantic, version bộ ca, metric tổng, metric theo nhóm và danh sách fail; không chỉ in console. **Tiêu chí nghiệm thu:** Mỗi lần chạy sinh đủ hai report UTF-8; tổng ca và từng fail truy ngược được về `case_id`; số liệu JSON và Markdown khớp 100%. **Rủi ro:** **Thấp** - report thiếu provenance khiến kết quả không tái lập.

---

## P4 - Cải thiện độ chính xác sau khi đã khóa an toàn và QA

**Gate P4/release:** Trên holdout độc lập: `red_flag_drug_count=0`, safety recall 100%, đúng nhóm >=70%, precision khi gợi ý >=80%, coverage >=60%, abstain accuracy >=90%, high-risk false positive = 0, diagnosis contradiction = 0, contract failure = 0.

- [ ] **P4.1 Audit và siết từng rule theo bằng chứng đặc hiệu** — **File/vùng code:** `backend/app.py:1706-1778`, `1925-1972`, `2088-2210`, chuỗi ưu tiên `2850-2871`. **Mô tả:** Với mỗi rule, ghi rõ điều kiện bắt buộc, loại trừ, mức rủi ro và lý do ưu tiên. Ưu tiên siết `psych`, `cardiac`, `urinary`, `wound_infection`, `infectious_bloody_diarrhea`, `antiviral_skin`, `bronchodilator`, `gastrointestinal`, `musculoskeletal_nsaid`. **Tiêu chí nghiệm thu:** Trên calibration set, precision tổng của các rule >=80%; rule có ít nhất 5 ca positive phải đạt precision >=80%, rule thiếu support phải ghi “chưa đủ dữ liệu” thay vì kết luận đạt; mỗi rule high-risk có ít nhất 3 negative controls và false positive bằng 0; không rule high-risk nào kích hoạt từ một symptom chung. **Rủi ro:** **Rất cao** - rule siết quá mức giảm recall; rule lỏng gây gợi ý thuốc sai.

- [ ] **P4.2 Sửa thứ tự ưu tiên rule để triage và nguyên nhân chính thắng symptom phụ** — **File/vùng code:** `backend/app.py:2850-2871`. **Mô tả:** Đau khu trú dữ dội, cờ đỏ hô hấp/thần kinh và bối cảnh nguy hiểm phải thắng buồn nôn/đau bụng chung; không để symptom phụ kéo ca sang chống nôn/dạ dày. **Tiêu chí nghiệm thu:** 100% ca có symptom phụ trong red flag vẫn bị safety block; **0** ca đau hố chậu phải bị rule chống nôn/dạ dày; không làm tăng red flag false negative. **Rủi ro:** **Rất cao** - thay thứ tự có thể tạo regression nhiều rule khác.

- [ ] **P4.3 Hiệu chỉnh confidence/top-gap trên calibration set, không tune holdout** — **File/vùng code:** `backend/app.py:69-83`, `2914-2940`; metadata model nếu cần. **Mô tả:** Quét có kiểm soát `MIN_RELIABLE_CONFIDENCE`, `MIN_HIGH_RISK_MODEL_CONFIDENCE`, `MIN_TOPGAP`; chọn ngưỡng theo safety, precision và coverage, không theo accuracy tổng. **Tiêu chí nghiệm thu:** Trên calibration set, đạt `red_flag_drug_count=0`, precision >=80%, coverage >=60%; ngưỡng và bảng thử nghiệm được ghi report; không đọc holdout để chọn ngưỡng. **Rủi ro:** **Cao** - ngưỡng cao tạo abstain hàng loạt, ngưỡng thấp tăng false positive.

- [ ] **P4.4 Cải thiện trích triệu chứng, thời gian, vị trí và phủ định** — **File/vùng code:** `backend/app.py:334-542`, `561-765`, `1370-1567`. **Mô tả:** Bổ sung pattern có cấu trúc cho thời gian kéo dài, vị trí hố chậu phải, mức độ dữ dội, tuổi/trẻ em và phủ định; hạn chế một phrase kích hoạt nhiều composite feature không liên quan. **Tiêu chí nghiệm thu:** Trên ít nhất 30 fixture extraction độc lập, precision feature >=90%, recall >=85%, negated-feature leakage bằng 0; ba red flag mục tiêu được map đủ tín hiệu. **Rủi ro:** **Cao** - mapping mới có thể làm model/rule kích hoạt ngoài ý muốn.

- [ ] **P4.5 Cải thiện nhóm cơ-xương-khớp nhưng không gắn bệnh cụ thể** — **File/vùng code:** `backend/app.py:334-542`, `2153-2163`, `2443-2491`, `2555-2571`; independent cases trong `scripts/`. **Mô tả:** Phủ các ca đau cơ sau vận động, bong gân, đau lưng sau bê nặng bằng nhãn hội chứng/cơ chế; chỉ gợi ý nhóm giảm đau/kháng viêm khi không có chấn thương nặng, sốt, yếu/tê tiến triển hoặc chống chỉ định. **Tiêu chí nghiệm thu:** Tối thiểu 8 ca cơ-xương độc lập đạt >=75% đúng nhóm chấp nhận; 100% không xuất nhãn bệnh cột sống/thoái hóa không có bằng chứng; ca có red flag thần kinh/chấn thương nặng không nhận thuốc. **Rủi ro:** **Cao** - NSAID có chống chỉ định và dễ bị rule quá rộng.

- [ ] **P4.6 Chặn model tự tin với nhóm hiếm/rủi ro cao** — **File/vùng code:** `backend/app.py:72-78`, `2918-2928`; `models/metadata.json`; có thể sửa `scripts/train_model.py` nếu cần retrain. **Mô tả:** Mở rộng high-risk policy cho ung thư, chống đông/kháng tiểu cầu, điều hòa miễn dịch và các nhóm có rất ít mẫu; mặc định abstain nếu thiếu bằng chứng đặc hiệu. **Tiêu chí nghiệm thu:** `high_risk_false_positive=0` trên calibration và holdout; ca ho kéo dài/sụt cân không bao giờ hiển thị “thuốc/điều trị ung thư”; report nêu riêng precision/recall nhóm hiếm, không che bằng accuracy tổng. **Rủi ro:** **Rất cao** - thay nhóm/ngưỡng có thể che một số ca thật; an toàn được ưu tiên hơn coverage.

- [ ] **P4.7 Chỉ retrain khi rule/extraction/threshold chưa đạt gate** — **File/vùng code:** `scripts/train_model.py`, `data/` nguồn train, `models/disease_model.joblib`, `models/metadata.json`. **Mô tả:** Nếu sau P4.1-P4.6 đúng nhóm vẫn dưới 70%, audit label leakage, class imbalance và nhóm chỉ có 10-28 mẫu trước khi retrain. Không augment bằng tri thức y khoa tự bịa; lưu source hash, class metrics và calibration. **Tiêu chí nghiệm thu:** Model mới chỉ được chọn nếu holdout đạt toàn bộ gate P4 và không giảm safety; metadata ghi data source/hash, class counts, per-class precision/recall/F1; kết quả nội bộ không được trình bày như accuracy lâm sàng. **Rủi ro:** **Rất cao** - retrain trên dữ liệu lệch có thể tăng accuracy nội bộ nhưng giảm an toàn thực tế.

- [ ] **P4.8 Chốt release bằng báo cáo độc lập và smoke local** — **File/vùng code:** `scripts/independent_probe.py`, `scripts/score_independent_probe.py`, `scripts/stress_test_user_cases.py`, `frontend/script.js`, `backend/app.py`. **Mô tả:** Chạy holdout đúng một lần cho quyết định release, sau đó chạy stress/schema và smoke UI local; nếu fail bất kỳ gate an toàn nào thì không release dù đúng nhóm tăng. **Tiêu chí nghiệm thu:** Holdout đạt đồng thời: **0 red flag có thuốc**, safety recall **100%**, đúng nhóm **>=70%** tính cả abstain sai, precision khi gợi ý **>=80%**, coverage **>=60%**, abstain accuracy **>=90%**, high-risk false positive **0**, diagnosis contradiction **0**, contract failure **0**; `python backend/app.py` chạy local và UI render đủ trạng thái không lỗi console. **Rủi ro:** **Cao** - chạy/review holdout nhiều lần rồi tiếp tục tune sẽ làm mất tính độc lập.

---

## Thứ tự triển khai và lệnh nghiệm thu dự kiến

1. Hoàn tất P0 và chạy gate safety sau mỗi thay đổi.
2. Hoàn tất P1-P2, xác nhận API/UI không trình bày quá mức.
3. Khóa bộ ca P3 và checksum trước khi chỉnh rule/ngưỡng ở P4.
4. Dùng calibration split cho P4; chỉ dùng holdout ở gate release.

```powershell
python scripts/independent_probe.py
python scripts/score_independent_probe.py --split calibration
python scripts/stress_test_user_cases.py
python backend/app.py
```

Ở gate cuối:

```powershell
python scripts/score_independent_probe.py --split holdout
```

## Definition of Done

- P0-P4 được thực hiện tuần tự và mọi gate đều đạt bằng số liệu từ bộ độc lập.
- Không red flag nào nhận nhóm thuốc, tên thuốc, hoạt chất hoặc top prediction.
- Rule không hiển thị như confidence 100%.
- Không còn nhãn bệnh raw tiếng Anh hoặc nhãn mâu thuẫn trên holdout.
- API contract và status `200/400/422` không bị phá.
- Probe chạy offline, tái lập trên máy local, không phụ thuộc tải model qua mạng.
- Báo cáo công khai giới hạn dataset/model và không hứa chất lượng tương đương bác sĩ.
