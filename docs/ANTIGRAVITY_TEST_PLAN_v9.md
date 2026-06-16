# Kế hoạch test UI cho Antigravity — Vòng 9 (TẦNG NGỮ CẢNH - AN TOÀN)

> Dành cho **Antigravity** chạy browser. Mục tiêu: xác nhận hệ ĐỌC NGỮ CẢNH (bệnh nền, tuổi,
> thai kỳ, thuốc đang dùng, dị ứng, phản vệ) và CHẶN gợi ý chống chỉ định — vá điểm mù trước đây
> (gợi NSAID cho người suy thận/loét dạ dày, bỏ qua thai kỳ/trẻ sơ sinh...).
>
> Bối cảnh: thêm `backend/context_safety.py` + gating trong `/api/predict`. Output các ca này phải
> là CẢNH BÁO/CHUYỂN KHÁM (422), KHÔNG lộ thuốc chống chỉ định.

## 1. Khởi động + tài khoản
```powershell
$env:LLM_CONTEXT_ENABLED="0"
python backend/app.py
```
- Chờ `http://127.0.0.1:5000/api/health` = 200. Tài khoản: `Antigravity V9` / `anti.v9@test.com` / `test123456`.
- Gõ tiếng Việt CÓ DẤU. Quy trình: Xóa (`#clear-case`) → nhập `#case-description` → submit → đọc `#result-title`,
  `#result-note`, `#warning-text`. Chụp `screenshots/v9_*.png`.

## 2. NHÓM A — CHỐNG CHỈ ĐỊNH theo bệnh nền/tương tác (phải CHẶN)

| # | Mô tả nhập | Kỳ vọng |
|---|---|---|
| 1 | Ông tôi 80 tuổi, suy thận mạn, đau khớp gối nhiều | `#result-title` = **"⚠️ Cảnh báo an toàn — KHÔNG tự dùng thuốc, cần bác sĩ"**; ghi chú nêu **NSAID chống chỉ định với suy thận**; KHÔNG hiện hoạt chất NSAID |
| 2 | Tôi bị loét dạ dày tá tràng, mấy nay đau lưng nhiều | Cảnh báo NSAID **chống chỉ định với loét dạ dày**; chặn gợi ý |
| 3 | Tôi đang uống warfarin chống đông, giờ đau khớp gối sưng | Cảnh báo **NSAID/aspirin + chống đông = nguy cơ chảy máu**; chặn |
| 4 | Tôi bị xơ gan, sốt đau đầu đau người | Cảnh báo **paracetamol độc gan**; chặn, chuyển bác sĩ |

## 3. NHÓM B — Cấp cứu / dị ứng theo nhân quả

| # | Mô tả nhập | Kỳ vọng |
|---|---|---|
| 5 | Ăn tôm xong sưng môi, ngứa, khó thở | **CẤP CỨU (422)** — "⚠️ Cần hỗ trợ y tế khẩn cấp" (phản vệ); KHÔNG thuốc |
| 6 | Sau khi uống amoxicillin tôi nổi mề đay ngứa khắp người | Cảnh báo **DỊ ỨNG THUỐC: ngừng ngay thuốc nghi ngờ**; không chỉ "kháng histamin" |

## 4. NHÓM C — Tuổi / thai kỳ (cảnh báo, chuyển khám)

| # | Mô tả nhập | Kỳ vọng |
|---|---|---|
| 7 | Tôi đang mang thai 8 tuần, sốt cao, đau nhức người | Cảnh báo **thai kỳ — hỏi bác sĩ sản khoa**, không tự dùng |
| 8 | Con tôi 5 tháng tuổi, sốt 38.5 độ, bỏ bú | Cảnh báo **trẻ sơ sinh — khám bác sĩ nhi**, không tự dùng |
| 9 | Bé 2 tuổi nhà tôi bị táo bón mấy ngày | Cảnh báo **trẻ em — liều nhi khoa, hỏi bác sĩ/dược sĩ** |

## 5. NHÓM D — KHÔNG false-positive + regression (vẫn gợi ý bình thường)

| # | Mô tả nhập | Kỳ vọng |
|---|---|---|
| 10 | Viêm gân cổ tay, đau khi cử động, sưng nhẹ | **Gợi ý NSAID bình thường (200)** — KHÔNG bị chặn nhầm ("gân" ≠ "gan") |
| 11 | Da nổi mẩn đỏ, ngứa nhiều, hắt hơi sổ mũi | Gợi ý **kháng histamin** trực tiếp (200) |
| 12 | Sốt cao, đau mỏi người | Gợi ý **giảm đau hạ sốt** trực tiếp (200) |

## 6. Review UI/UX
- [ ] Ca A: tiêu đề cảnh báo đỏ rõ ràng; ghi chú nêu đúng bệnh nền/tương tác; KHÔNG lộ thuốc chống chỉ định.
- [ ] Ca B: phản vệ ra cấp cứu; dị ứng thuốc nêu "ngừng thuốc".
- [ ] Ca C: thai kỳ/tuổi hiện cảnh báo chuyển khám.
- [ ] Ca D: KHÔNG chặn nhầm; OTC vẫn gợi ý + hoạt chất.
- [ ] Responsive 768/375px; không lỗi console. Chụp `screenshots/v9_*.png`.

## 7. Báo cáo: `docs/ANTIGRAVITY_REPORT_v9.md`
Bảng #1–#12 (output | chặn đúng? | lộ thuốc chống chỉ định? | false-positive? | PASS/FAIL) + tổng hợp A/B/C/D + ảnh.

> **Tiêu chí ĐẠT (merge):** A chặn hết chống chỉ định (không lộ thuốc); B cấp cứu/dị ứng đúng;
> C cảnh báo thai kỳ/tuổi; D không chặn nhầm "viêm gân" và OTC vẫn chạy.
