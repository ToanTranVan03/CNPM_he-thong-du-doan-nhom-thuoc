import unittest
import json
# Import app từ file route_auth của bạn để test
from backend.route_auth import app 

class TestAuthAPI(unittest.TestCase):
    def setUp(self):
        # Thiết lập môi trường test ảo
        self.app = app.test_client()
        self.app.testing = True

    def test_login_success(self):
        # Kịch bản 1: Nhập đúng tài khoản -> Phải trả về mã 200 và có Token
        payload = {'email': 'admin@gmail.com', 'password': '123456'}
        response = self.app.post('/api/login', 
                                 data=json.dumps(payload), 
                                 content_type='application/json')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['message'], 'Đăng nhập thành công')
        self.assertIn('token', data)

    def test_login_fail(self):
        # Kịch bản 2: Nhập sai mật khẩu -> Phải trả về mã 401 và báo lỗi
        payload = {'email': 'admin@gmail.com', 'password': 'sai_mat_khau_ne'}
        response = self.app.post('/api/login', 
                                 data=json.dumps(payload), 
                                 content_type='application/json')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 401)
        self.assertEqual(data['message'], 'Sai email hoặc mật khẩu')

if __name__ == '__main__':
    unittest.main()