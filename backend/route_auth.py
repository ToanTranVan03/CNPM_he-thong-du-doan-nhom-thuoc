from flask import Flask, request, jsonify
import jwt
import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev_key_bi_mat' # Key này để mã hóa token

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    # Hardcode tạm để test, sau này nối với MySQL của Hương sau
    if email == "admin@gmail.com" and password == "123456":
        token = jwt.encode({
            'user': email,
            'role': 'Admin',
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, app.config['SECRET_KEY'], algorithm="HS256")
        
        return jsonify({'message': 'Đăng nhập thành công', 'token': token}), 200
    
    return jsonify({'message': 'Sai email hoặc mật khẩu'}), 401
if __name__ == '__main__':
    app.run(debug=True, port=5000)