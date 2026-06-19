from flask import Flask, request, jsonify
from flask_cors import CORS
import jwt
import datetime
from models import db, User 

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = 'dev_key_bi_mat' 


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pharma_predict.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')


    if email == "admin@gmail.com" and password == "123456":
        token = jwt.encode({
            'user': email,
            'role': 'Admin',
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, app.config['SECRET_KEY'], algorithm="HS256")
        
        return jsonify({'message': 'Đăng nhập thành công', 'token': token}), 200
    
    return jsonify({'message': 'Sai email hoặc mật khẩu'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():

    return jsonify({'message': 'Đăng xuất thành công, token đã bị vô hiệu hóa ở client'}), 200


@app.route('/api/users/change-password', methods=['PUT'])
def change_password():

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"error": "Chưa đăng nhập hoặc thiếu mã xác thực Token"}), 401
    
    token = auth_header.split(" ")[1]

    try:
  
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        email = payload['user']
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Phiên làm việc đã hết hạn, vui lòng đăng nhập lại"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Mã xác thực Token không hợp lệ"}), 401


    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "Tài khoản người dùng không tồn tại"}), 404


    data = request.get_json() or {}
    old_password = data.get('old_password')
    new_password = data.get('new_password')

    if not old_password or not new_password:
        return jsonify({"error": "Vui lòng nhập đầy đủ thông tin mật khẩu cũ và mới"}), 400


    if not user.check_password(old_password):
        return jsonify({"error": "Mật khẩu cũ nhập vào không chính xác"}), 400


    user.set_password(new_password)
    db.session.commit() 

    return jsonify({"message": "Thay đổi mật khẩu tài khoản thành công!"}), 200
if __name__ == '__main__':
    app.run(debug=True, port=5000)