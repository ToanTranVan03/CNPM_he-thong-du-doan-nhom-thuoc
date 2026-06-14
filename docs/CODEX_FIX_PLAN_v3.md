# CODEX_FIX_PLAN_v3

> Vai trò Codex: lập plan, không sửa code. Plan này dành cho Claude/agent triển khai fix 2 ca fail nghiêm trọng trong Antigravity Test V3, ưu tiên không kê sai thuốc hơn là cố ép đúng nhãn.

## Mục tiêu

- Chặn ca #9 không còn trả `thuốc kháng sinh` tự tin cho cụm nghi sốt rét sau đi vùng rừng núi.
- Chặn ca #10 không còn trả `thuốc tim mạch/huyết áp` cho cụm nghi thiếu máu/thiếu vi chất.
- Không làm regress các ca đang PASS: Mức 4 `8/8`, Mức 6 `4/4`.
- Sau fix phải chạy lại `python scripts/eval_vietnamese.py` và giao Antigravity test lại #9, #10.

## Phân tích hiện trạng

- `backend/app.py:65`: `MIN_RELIABLE_CONFIDENCE = 0.5`. Ca #10 đang `53.2%`, nên có thể lọt qua ngưỡng hiện tại.
- `backend/app.py:1700`: `emergency_red_flag_from_notes(notes)` chạy trước model, dành cho cấp cứu rõ như đột quỵ, viêm màng não, tim mạch. Không nên nhét #9/#10 vào cổng cấp cứu 422 này nếu chỉ cần "đi khám/xin thêm thông tin".
- `backend/app.py:2469-2487`: `rule_group` có thể override model và đặt `score_type = "rule"`. Nếu thêm rule ở đây phải rất đặc hiệu, vì rule sẽ bypass một số kiểm tra thiếu dữ liệu.
- `backend/app.py:2496-2545`: `quality_reasons` là nơi phù hợp để chặn kê thuốc và trả `needs_more_input=True`/HTTP 422.
- `backend/app.py:503-515`: `UNSUPPORTED_SYMPTOM_KEYWORDS` hiện gần như chỉ có mất ngủ; chưa có `da xanh xao`, `niêm nhợt`, yếu tố dịch tễ sốt rét.
- `backend/app.py:375`: `brittle_nails` có `móng giòn`, `móng dễ gãy`, nhưng chưa chắc bắt được cụm `móng tay giòn` do không liền từ.
- `data/test_vi_cases.csv` đã có ca sốt rét và thiếu máu tương tự; `data/test_vi_cases_v3.csv` có `w29`, `w32` gần với #10, #9.

## Checklist Triển Khai

- [ ] **Bước 1: Chụp baseline trước khi sửa**
  - Chạy `python scripts/eval_vietnamese.py`.
  - Chạy thêm `python scripts/eval_vietnamese.py --cases data/test_vi_cases_v3.csv`.
  - Ghi lại các dòng fail hiện tại, đặc biệt ca có nội dung `Sốt thành cơn...` và `Mệt mỏi, da xanh xao...`.

- [ ] **Bước 2: Bổ sung nhận diện keyword tối thiểu cho thiếu máu**
  - File: `backend/app.py`.
  - Vị trí: gần `VI_SYMPTOM_KEYWORDS`, dòng khoảng `330-440`.
  - Thêm biến thể cho `brittle_nails`: `móng tay giòn`, `móng tay dễ gãy`, `móng giòn dễ gãy`.
  - Không thêm `da xanh xao` thành một triệu chứng train chung nếu chưa có feature tương ứng ổn định; dùng nó trong helper theo `notes` thô để tránh kéo model lệch.

- [ ] **Bước 3: Thêm helper nhận diện cụm sốt rét có yếu tố dịch tễ**
  - File: `backend/app.py`.
  - Vị trí đề xuất: sau `emergency_red_flag_from_notes(notes)` hoặc ngay trước block rule cluster ở khoảng `backend/app.py:1777`.
  - Tên helper đề xuất: `has_malaria_epidemiology_pattern(notes: str, active_symptoms: set[str]) -> bool`.
  - Điều kiện kích hoạt phải đủ chặt:
    - Có cụm sốt theo cơn: `sot thanh con`, `sot tung con`, `sot ret run`, hoặc có `fever/high fever/mild fever` kèm `chills/shivering`.
    - Có `rét run/run rẩy/lạnh run` qua `active_symptoms` hoặc `normalize(notes)`.
    - Có `vã mồ hôi/đổ mồ hôi/sweating`.
    - Có yếu tố dịch tễ: `vung rung nui`, `rung nui`, `di rung`, `vung sot ret`, `mien nui`, `moi o vung rung`, `vua di ... ve`.
  - Giảm false-positive:
    - Không kích hoạt nếu chỉ có `sốt + rét run` nhưng không có yếu tố dịch tễ.
    - Không kích hoạt cho ca hô hấp thông thường có `ho/sổ mũi/đau họng` nếu thiếu yếu tố dịch tễ.
    - Không dùng ngưỡng confidence để fix #9 vì ca fail đang `81.3%`.

- [ ] **Bước 4: Chọn hành vi cho #9**
  - File: `backend/app.py`.
  - Vị trí: `rule_group` tại `backend/app.py:2469-2487` hoặc `quality_reasons` tại `backend/app.py:2496-2545`.
  - Khuyến nghị:
    - Nếu helper #9 đủ đặc hiệu, thêm `malaria_rule_drug_group(notes, active_symptoms)` vào đầu `rule_group` và trả `thuốc điều trị sốt rét`.
    - Đồng thời đảm bảo guidance/warning nói rõ: cần đi khám/xét nghiệm sốt rét sớm, không tự dùng thuốc điều trị sốt rét.
  - Phương án an toàn tối thiểu nếu chưa muốn kê nhóm sốt rét: không set `rule_group`; append `quality_reasons` để trả `needs_more_input=True`. Antigravity #9 vẫn PASS tối thiểu vì không còn kê `thuốc kháng sinh`, nhưng có thể làm fail các eval case đang kỳ vọng `thuốc điều trị sốt rét`, nên phải cân nhắc sau khi chạy `eval_vietnamese`.

- [ ] **Bước 5: Thêm helper nhận diện cụm thiếu máu/thiếu vi chất**
  - File: `backend/app.py`.
  - Vị trí đề xuất: cùng vùng helper lâm sàng với #9, trước `should_force_more_info` hoặc trước block `quality_reasons`.
  - Tên helper đề xuất: `has_anemia_like_pattern(notes: str, active_symptoms: set[str]) -> bool`.
  - Điều kiện kích hoạt:
    - Có mệt: `fatigue` hoặc phrase `met moi`, `met`, `u oai`.
    - Có chóng mặt/hoa mắt: `dizziness` hoặc phrase tương ứng.
    - Có da/niêm nhợt: `da xanh`, `da xanh xao`, `niem nhot`, `niem mac nhot`, `moi nhot`, `long ban tay nhot`.
    - Có móng giòn/dễ gãy: `brittle_nails` hoặc phrase `mong tay gion`, `mong de gay`.
  - Hành vi: append vào `quality_reasons`, trả `needs_more_input=True`, không trả `thuốc tim mạch/huyết áp`.
  - Giảm false-positive:
    - Không kích hoạt chỉ vì `mệt + chóng mặt`; cụm phải có ít nhất dấu da/niêm nhợt và móng giòn.
    - Không chặn ca tim mạch thật như `huyết áp 160...` hoặc `tim đập nhanh không đều, hụt hơi, choáng` vì các ca đó không có `da xanh/niêm nhợt + móng giòn`.
    - Không ép ngay sang `vitamin và khoáng chất` nếu chưa có bằng chứng đủ; với thiếu máu cần xét nghiệm và phân biệt thiếu sắt, B12/folate, mất máu, bệnh mạn.

- [ ] **Bước 6: Rà lại ngưỡng confidence**
  - File: `backend/app.py`.
  - Vị trí: `MIN_RELIABLE_CONFIDENCE` tại dòng khoảng `65` và check tại `backend/app.py:2530`.
  - Không fix #9 bằng ngưỡng vì `81.3%`.
  - Với #10, không tăng global threshold tùy tiện nếu làm regress ca đang PASS.
  - Khuyến nghị thêm ngưỡng scoped cho model-only prediction nhóm rủi ro, ví dụ `MIN_HIGH_RISK_MODEL_CONFIDENCE = 0.60` áp dụng khi `score_type != "rule"` và `prediction` thuộc nhóm như `thuốc tim mạch/huyết áp`, `thuốc kháng sinh`, `thuốc thần kinh/tâm thần`.
  - Nếu scoped threshold làm fail ca hợp lệ, ưu tiên giữ helper #10 và không tăng threshold global.

- [ ] **Bước 7: Điều chỉnh prompt/triage cho #9/#10**
  - File: `backend/app.py`.
  - Vị trí: `symptom_triage_guidance(active_symptoms)` khoảng `backend/app.py:1069`, `suggested_symptoms_for_more_info(active_symptoms)` khoảng `1988`, `more_info_prompt(active_symptoms)` khoảng `2078`.
  - Nếu #10 trả 422, message nên hỏi thêm: thời gian mệt, mức độ chóng mặt/ngất, kinh nguyệt/chảy máu, ăn uống, thai kỳ, bệnh nền, xét nghiệm máu gần đây.
  - Nếu #9 trả 422 thay vì đúng nhóm sốt rét, message nên yêu cầu đi khám/xét nghiệm sốt rét sớm và hỏi thêm số ngày sốt, nhiệt độ, nôn/tiêu chảy, vàng da, lơ mơ, nơi đã đi.
  - Không làm thay đổi cổng cấp cứu Mức 6 đang PASS.

- [ ] **Bước 8: Thêm regression coverage**
  - Nếu có test backend riêng, thêm test Flask client cho `/api/predict`:
    - `Sốt thành cơn, rét run rồi vã mồ hôi, vừa đi vùng rừng núi về` không được trả `thuốc kháng sinh`.
    - `Mệt mỏi, da xanh xao, chóng mặt, móng tay giòn` phải trả 422 hoặc không được trả `thuốc tim mạch/huyết áp`.
  - Nếu chỉ dùng CSV eval, thêm/đối chiếu biến thể với `data/test_vi_cases_v3.csv` nhưng không sửa expected chỉ để che lỗi. Nếu tiêu chí chính thức chấp nhận `NEEDS_MORE_INFO` cho #10, thêm vào `also_ok` sau khi thống nhất với báo cáo V3.

- [ ] **Bước 9: Verify bằng eval**
  - Chạy `python scripts/eval_vietnamese.py`.
  - Chạy `python scripts/eval_vietnamese.py --cases data/test_vi_cases_v3.csv`.
  - Điều kiện đạt:
    - Không có regress ở các nhóm đang PASS, đặc biệt các ca tương ứng Mức 4 và Mức 6.
    - #9 không còn dự đoán `thuốc kháng sinh`.
    - #10 không còn dự đoán `thuốc tim mạch/huyết áp`.
    - Nếu #9 trả `thuốc điều trị sốt rét`, kiểm tra warning không khuyến khích tự dùng thuốc.
    - Nếu #10 trả 422, kiểm tra response có `needs_more_input=True`, `display_title` là `Chưa đủ dữ liệu để gợi ý thuốc`.

- [ ] **Bước 10: Giao Antigravity test lại**
  - Chạy lại app bằng `python backend/app.py`.
  - Giao Antigravity test lại đúng #9 và #10:
    - #9: `Sốt thành cơn, rét run rồi vã mồ hôi, vừa đi vùng rừng núi về`.
    - #10: `Mệt mỏi, da xanh xao, chóng mặt, móng tay giòn`.
  - Yêu cầu báo cáo ghi rõ `#summary-drug-group`, `#confidence-value`, `needs_more/cảnh báo`.
  - PASS tối thiểu:
    - #9 không trả `thuốc kháng sinh` tự tin.
    - #10 không trả `thuốc tim mạch/huyết áp` tự tin.
    - Mức 4 vẫn `8/8`, Mức 6 vẫn `4/4`.

## Rủi ro Và Cách Giảm

- Rủi ro #9 false-positive với cúm/sốt virus: giảm bằng cách bắt buộc có yếu tố dịch tễ `rừng núi/vùng sốt rét/vừa đi vùng nguy cơ`.
- Rủi ro #10 chặn nhầm tim mạch: giảm bằng cách yêu cầu đủ `mệt + chóng mặt + da/niêm nhợt + móng giòn`; không chặn chỉ vì `choáng/hồi hộp/hụt hơi`.
- Rủi ro tăng threshold làm regress ca thường: dùng threshold scoped cho `score_type != "rule"` và nhóm thuốc rủi ro; rollback threshold nếu eval fail rộng.
- Rủi ro rule kê thuốc quá mạnh: với #10 không kê `vitamin và khoáng chất` ngay; với #9 chỉ trả `thuốc điều trị sốt rét` khi đủ cụm rất đặc hiệu, còn lại chuyển 422.
