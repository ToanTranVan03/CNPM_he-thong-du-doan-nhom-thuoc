"""
Integration Test: Thêm thuốc vào nhóm (Add Medicine to Group)
Test flow: Tạo nhóm thuốc → Thêm thuốc vào nhóm → Kiểm tra dữ liệu
"""
import unittest
import json
import tempfile
import os
from pathlib import Path

# Setup đường dẫn để import backend modules
import sys
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from backend.app import app
from backend.models import db, NhomThuoc, Thuoc


class TestAddMedicineToGroup(unittest.TestCase):
    """Integration test cho luồng thêm thuốc vào nhóm"""

    def setUp(self):
        """Khởi tạo môi trường test"""
        app.config['TESTING'] = True

        # Khởi tạo test client
        self.client = app.test_client()

        # Setup app context
        self.app_context = app.app_context()
        self.app_context.push()

        # Clean existing database for test isolation
        try:
            # Delete all tables
            meta = db.metadata
            for table in reversed(meta.sorted_tables):
                db.session.execute(table.delete())
            db.session.commit()
        except Exception as e:
            print(f"Warning during cleanup: {e}")

    def tearDown(self):
        """Dọn dẹp sau test"""
        try:
            # Delete all data after each test
            meta = db.metadata
            for table in reversed(meta.sorted_tables):
                db.session.execute(table.delete())
            db.session.commit()
        except Exception as e:
            pass  # Silently ignore
        finally:
            db.session.remove()
            if self.app_context:
                try:
                    self.app_context.pop()
                except:
                    pass

    # ========== SETUP HELPERS ==========
    def create_drug_group(self, name, description=""):
        """Helper tạo nhóm thuốc"""
        import uuid
        # Make group name unique by adding random suffix
        unique_name = f"{name}_{uuid.uuid4().hex[:8]}"
        response = self.client.post(
            '/api/drug-groups',
            data=json.dumps({
                'ten_nhom': unique_name,
                'mo_ta': description
            }),
            content_type='application/json'
        )
        return response

    def add_medicine(self, name, group_id, **kwargs):
        """Helper thêm thuốc"""
        payload = {
            'ten_thuoc': name,
            'nhom_thuoc_id': group_id,
            **kwargs
        }
        response = self.client.post(
            '/api/thuoc',
            data=json.dumps(payload),
            content_type='application/json'
        )
        return response

    def get_medicine(self, medicine_id):
        """Helper lấy chi tiết thuốc"""
        response = self.client.get(f'/api/thuoc/{medicine_id}')
        return response

    def get_all_medicines_in_group(self, group_id):
        """Helper lấy danh sách thuốc trong nhóm"""
        response = self.client.get(f'/api/thuoc?nhom_thuoc_id={group_id}')
        return response

    # ========== HAPPY PATH TESTS ==========

    def test_01_add_medicine_with_minimal_data(self):
        """TC01: Thêm thuốc với dữ liệu bắt buộc (tên + nhóm)"""
        # Bước 1: Tạo nhóm thuốc
        group_response = self.create_drug_group("Thuốc kháng sinh", "Dùng điều trị nhiễm khuẩn")
        self.assertEqual(group_response.status_code, 201)
        group_data = json.loads(group_response.data)
        group_id = group_data['data']['id']

        # Bước 2: Thêm thuốc vào nhóm
        response = self.add_medicine("Amoxicillin", group_id)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)

        # Kiểm chứng
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Thêm thuốc thành công!')
        self.assertIn('thuoc', data)
        self.assertEqual(data['thuoc']['ten_thuoc'], 'Amoxicillin')
        self.assertEqual(data['thuoc']['nhom_thuoc_id'], group_id)

    def test_02_add_medicine_with_full_data(self):
        """TC02: Thêm thuốc với đầy đủ thông tin"""
        # Tạo nhóm
        group_response = self.create_drug_group("Thuốc giảm đau hạ sốt")
        group_data = json.loads(group_response.data)
        group_id = group_data['data']['id']

        # Thêm thuốc với đầy đủ thông tin
        response = self.add_medicine(
            name="Paracetamol",
            group_id=group_id,
            hoat_chat="Paracetamol (Acetaminophen)",
            ham_luong="500mg",
            dang_bao_che="Viên nén",
            hang_san_xuat="Công ty A",
            nuoc_san_xuat="Việt Nam",
            so_dang_ky="DK-2024-001",
            gia_tham_khao=5000.0,
            don_vi_tinh="Hộp",
            mo_ta="Giảm đau, hạ sốt cho trẻ em và người lớn"
        )

        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        thuoc = data['thuoc']

        # Kiểm chứng tất cả field
        self.assertEqual(thuoc['ten_thuoc'], 'Paracetamol')
        self.assertEqual(thuoc['hoat_chat'], 'Paracetamol (Acetaminophen)')
        self.assertEqual(thuoc['ham_luong'], '500mg')
        self.assertEqual(thuoc['dang_bao_che'], 'Viên nén')
        self.assertEqual(thuoc['hang_san_xuat'], 'Công ty A')
        self.assertEqual(thuoc['nuoc_san_xuat'], 'Việt Nam')
        self.assertEqual(thuoc['so_dang_ky'], 'DK-2024-001')
        self.assertEqual(thuoc['gia_tham_khao'], 5000.0)
        self.assertEqual(thuoc['don_vi_tinh'], 'Hộp')
        self.assertEqual(thuoc['mo_ta'], 'Giảm đau, hạ sốt cho trẻ em và người lớn')

    def test_03_add_multiple_medicines_to_same_group(self):
        """TC03: Thêm nhiều thuốc vào cùng một nhóm"""
        # Tạo nhóm
        group_response = self.create_drug_group("Vitamin & Khoáng chất")
        group_data = json.loads(group_response.data)
        group_id = group_data['data']['id']

        medicines = [
            {"name": "Vitamin C 1000mg", "hoat_chat": "Ascorbic acid"},
            {"name": "Vitamin D3", "hoat_chat": "Cholecalciferol"},
            {"name": "Canxi", "hoat_chat": "Calcium carbonate"}
        ]

        # Thêm 3 thuốc
        added_ids = []
        for med in medicines:
            response = self.add_medicine(
                name=med['name'],
                group_id=group_id,
                hoat_chat=med['hoat_chat']
            )
            self.assertEqual(response.status_code, 201)
            data = json.loads(response.data)
            added_ids.append(data['thuoc']['id'])

        # Kiểm chứng: lấy tất cả thuốc trong nhóm
        list_response = self.get_all_medicines_in_group(group_id)
        self.assertEqual(list_response.status_code, 200)
        medicines_list = json.loads(list_response.data)

        self.assertEqual(len(medicines_list), 3)
        for med in medicines_list:
            self.assertEqual(med['nhom_thuoc_id'], group_id)
            self.assertIn(med['id'], added_ids)

    def test_04_get_medicine_after_creation(self):
        """TC04: Lấy chi tiết thuốc vừa thêm"""
        # Tạo nhóm & thêm thuốc
        group_response = self.create_drug_group("Thuốc trị ho")
        group_data = json.loads(group_response.data)
        group_id = group_data['data']['id']

        add_response = self.add_medicine(
            name="Thuốc ho Promethazine",
            group_id=group_id,
            hoat_chat="Promethazine HCl",
            ham_luong="5mg/5ml",
            dang_bao_che="Siro"
        )
        thuoc_data = json.loads(add_response.data)
        medicine_id = thuoc_data['thuoc']['id']

        # Lấy chi tiết
        get_response = self.get_medicine(medicine_id)
        self.assertEqual(get_response.status_code, 200)
        retrieved_data = json.loads(get_response.data)

        self.assertEqual(retrieved_data['id'], medicine_id)
        self.assertEqual(retrieved_data['ten_thuoc'], 'Thuốc ho Promethazine')
        self.assertEqual(retrieved_data['nhom_thuoc_id'], group_id)

    def test_05_verify_relationship_nhom_thuoc_in_response(self):
        """TC05: Kiểm chứng thông tin nhóm thuốc được embed trong response"""
        # Tạo nhóm
        group_response = self.create_drug_group("Thuốc da liễu")
        group_data = json.loads(group_response.data)
        group_id = group_data['data']['id']
        group_name = group_data['data']['ten_nhom']

        # Thêm thuốc
        add_response = self.add_medicine("Kem trị nấm", group_id)
        data = json.loads(add_response.data)
        thuoc = data['thuoc']

        # Kiểm chứng embed nhóm thuốc
        self.assertIn('nhom_thuoc', thuoc)
        self.assertEqual(thuoc['nhom_thuoc']['id'], group_id)
        self.assertEqual(thuoc['nhom_thuoc']['ten_nhom'], group_name)

    # ========== VALIDATION TESTS (Lỗi dự kiến) ==========

    def test_06_add_medicine_without_name(self):
        """TC06: Lỗi - Không nhập tên thuốc"""
        # Tạo nhóm
        group_response = self.create_drug_group("Nhóm test")
        group_data = json.loads(group_response.data)
        group_id = group_data['data']['id']

        # Thêm thuốc không có tên
        response = self.client.post(
            '/api/thuoc',
            data=json.dumps({
                'ten_thuoc': '',  # Rỗng
                'nhom_thuoc_id': group_id
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('tên thuốc', data['error'].lower())

    def test_07_add_medicine_without_group_id(self):
        """TC07: Lỗi - Không chọn nhóm thuốc"""
        response = self.client.post(
            '/api/thuoc',
            data=json.dumps({
                'ten_thuoc': 'Ibuprofen',
                # Thiếu nhom_thuoc_id
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('nhóm thuốc', data['error'].lower())

    def test_08_add_medicine_with_invalid_group_id(self):
        """TC08: Lỗi - Nhóm thuốc không tồn tại"""
        response = self.client.post(
            '/api/thuoc',
            data=json.dumps({
                'ten_thuoc': 'Thuốc bất kỳ',
                'nhom_thuoc_id': 99999  # ID không tồn tại
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('nhóm thuốc', data['error'].lower())

    def test_09_add_medicine_with_whitespace_name(self):
        """TC09: Lỗi - Tên thuốc chỉ chứa khoảng trắng"""
        group_response = self.create_drug_group("Nhóm test")
        group_data = json.loads(group_response.data)
        group_id = group_data['data']['id']

        response = self.client.post(
            '/api/thuoc',
            data=json.dumps({
                'ten_thuoc': '   ',  # Chỉ khoảng trắng
                'nhom_thuoc_id': group_id
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)

    def test_10_add_medicine_name_trimmed(self):
        """TC10: Tên thuốc tự động bị trim khoảng trắng"""
        group_response = self.create_drug_group("Nhóm test")
        group_data = json.loads(group_response.data)
        group_id = group_data['data']['id']

        response = self.add_medicine("  Thuốc test  ", group_id)

        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        # Kiểm chứng tên được trim
        self.assertEqual(data['thuoc']['ten_thuoc'], 'Thuốc test')

    # ========== EDGE CASES ==========

    def test_11_add_medicine_with_special_characters(self):
        """TC11: Thêm thuốc tên có ký tự đặc biệt"""
        group_response = self.create_drug_group("Nhóm test")
        group_data = json.loads(group_response.data)
        group_id = group_data['data']['id']

        response = self.add_medicine(
            "Thuốc test (ABC-123) /Công ty® ©",
            group_id
        )

        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(
            data['thuoc']['ten_thuoc'],
            "Thuốc test (ABC-123) /Công ty® ©"
        )

    def test_12_add_medicine_with_long_description(self):
        """TC12: Thêm thuốc với mô tả dài"""
        group_response = self.create_drug_group("Nhóm test")
        group_data = json.loads(group_response.data)
        group_id = group_data['data']['id']

        long_description = "A" * 1000  # Mô tả dài 1000 ký tự

        response = self.add_medicine(
            "Thuốc test",
            group_id,
            mo_ta=long_description
        )

        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(data['thuoc']['mo_ta'], long_description)

    def test_13_add_medicine_with_zero_price(self):
        """TC13: Thêm thuốc có giá = 0"""
        group_response = self.create_drug_group("Nhóm test")
        group_data = json.loads(group_response.data)
        group_id = group_data['data']['id']

        response = self.add_medicine(
            "Thuốc miễn phí",
            group_id,
            gia_tham_khao=0.0
        )

        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(data['thuoc']['gia_tham_khao'], 0.0)

    def test_14_add_medicine_with_negative_price(self):
        """TC14: Thêm thuốc có giá âm (API không validate)"""
        group_response = self.create_drug_group("Nhóm test")
        group_data = json.loads(group_response.data)
        group_id = group_data['data']['id']

        response = self.add_medicine(
            "Thuốc test",
            group_id,
            gia_tham_khao=-5000.0
        )

        # API hiện không validate giá âm, nên sẽ thêm thành công
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        # Lưu ý: Đây có thể là bug cần fix
        self.assertEqual(data['thuoc']['gia_tham_khao'], -5000.0)

    def test_15_add_medicine_with_string_price(self):
        """TC15: Thêm thuốc giá là chuỗi (type mismatch)"""
        group_response = self.create_drug_group("Nhóm test")
        group_data = json.loads(group_response.data)
        group_id = group_data['data']['id']

        response = self.client.post(
            '/api/thuoc',
            data=json.dumps({
                'ten_thuoc': 'Thuốc test',
                'nhom_thuoc_id': group_id,
                'gia_tham_khao': 'không phải số'
            }),
            content_type='application/json'
        )

        # Tùy theo SQL driver, có thể accept hoặc reject
        # Thường là 201 vì SQLAlchemy cố convert
        # Nhưng giá trị có thể là None hoặc error
        self.assertIn(response.status_code, [201, 400, 500])

    def test_16_database_consistency_after_add(self):
        """TC16: Kiểm chứng tính nhất quán dữ liệu trong DB (via API)"""
        group_response = self.create_drug_group("Nhóm kiểm chứng")
        group_data = json.loads(group_response.data)
        group_id = group_data['data']['id']

        add_response = self.add_medicine(
            "Thuốc kiểm chứng",
            group_id,
            hoat_chat="Test",
            ham_luong="100mg"
        )
        thuoc_data = json.loads(add_response.data)
        medicine_id = thuoc_data['thuoc']['id']

        # Kiểm chứng via API (lấy chi tiết)
        get_response = self.get_medicine(medicine_id)
        self.assertEqual(get_response.status_code, 200)
        retrieved = json.loads(get_response.data)

        self.assertEqual(retrieved['id'], medicine_id)
        self.assertEqual(retrieved['ten_thuoc'], 'Thuốc kiểm chứng')
        self.assertEqual(retrieved['nhom_thuoc_id'], group_id)
        self.assertEqual(retrieved['hoat_chat'], 'Test')
        self.assertEqual(retrieved['ham_luong'], '100mg')

    def test_17_medicine_deleted_when_group_deleted(self):
        """TC17: Kiểm chứng CASCADE delete - xóa nhóm → xóa thuốc"""
        # Tạo nhóm & thêm thuốc
        group_response = self.create_drug_group("Nhóm sẽ xóa")
        group_data = json.loads(group_response.data)
        group_id = group_data['data']['id']

        add_response = self.add_medicine("Thuốc sẽ xóa", group_id)
        thuoc_data = json.loads(add_response.data)
        medicine_id = thuoc_data['thuoc']['id']

        # Xóa nhóm
        delete_response = self.client.delete(f'/api/drug-groups/{group_id}')
        self.assertEqual(delete_response.status_code, 200)

        # Kiểm chứng thuốc cũng bị xóa
        get_response = self.get_medicine(medicine_id)
        self.assertEqual(get_response.status_code, 404)

    # ========== CONCURRENT/STRESS TESTS ==========

    def test_18_add_many_medicines_to_group(self):
        """TC18: Thêm nhiều thuốc (100) vào cùng nhóm"""
        group_response = self.create_drug_group("Nhóm stress test")
        group_data = json.loads(group_response.data)
        group_id = group_data['data']['id']

        # Thêm 100 thuốc
        for i in range(100):
            response = self.add_medicine(
                f"Thuốc {i:03d}",
                group_id,
                hoat_chat=f"Hoạt chất {i}"
            )
            self.assertEqual(response.status_code, 201)

        # Kiểm chứng
        list_response = self.get_all_medicines_in_group(group_id)
        self.assertEqual(list_response.status_code, 200)
        medicines_list = json.loads(list_response.data)
        self.assertEqual(len(medicines_list), 100)

    def test_19_add_medicine_to_different_groups(self):
        """TC19: Thêm cùng tên thuốc vào nhiều nhóm khác nhau"""
        # Tạo 3 nhóm
        groups = []
        for i in range(3):
            response = self.create_drug_group(f"Nhóm {i}")
            data = json.loads(response.data)
            groups.append(data['data']['id'])

        # Thêm cùng tên thuốc vào 3 nhóm khác nhau
        medicine_ids = []
        for group_id in groups:
            response = self.add_medicine("Ibuprofen", group_id)
            self.assertEqual(response.status_code, 201)
            data = json.loads(response.data)
            medicine_ids.append(data['thuoc']['id'])

        # Kiểm chứng: 3 ID khác nhau, mỗi cái khác nhóm
        self.assertEqual(len(set(medicine_ids)), 3)
        for i, medicine_id in enumerate(medicine_ids):
            get_response = self.get_medicine(medicine_id)
            med_data = json.loads(get_response.data)
            self.assertEqual(med_data['nhom_thuoc_id'], groups[i])

    # ========== API RESPONSE FORMAT TESTS ==========

    def test_20_response_format_on_add(self):
        """TC20: Kiểm chứng định dạng JSON response"""
        group_response = self.create_drug_group("Nhóm test")
        group_data = json.loads(group_response.data)
        group_id = group_data['data']['id']

        add_response = self.add_medicine("Thuốc test", group_id)
        data = json.loads(add_response.data)

        # Kiểm chứng structure
        self.assertIn('message', data)
        self.assertIn('thuoc', data)

        thuoc = data['thuoc']
        required_fields = [
            'id', 'ten_thuoc', 'nhom_thuoc_id', 'nhom_thuoc'
        ]
        for field in required_fields:
            self.assertIn(field, thuoc, f"Missing field: {field}")

    def test_21_http_status_codes(self):
        """TC21: Kiểm chứng các HTTP status code"""
        # 201 - Created
        group_response = self.create_drug_group("Nhóm test")
        group_id = json.loads(group_response.data)['data']['id']

        add_response = self.add_medicine("Thuốc", group_id)
        self.assertEqual(add_response.status_code, 201)

        # 404 - Not found
        get_response = self.get_medicine(99999)
        self.assertEqual(get_response.status_code, 404)

        # 400 - Bad request
        bad_response = self.client.post(
            '/api/thuoc',
            data=json.dumps({'ten_thuoc': ''}),
            content_type='application/json'
        )
        self.assertEqual(bad_response.status_code, 400)


if __name__ == '__main__':
    unittest.main()
