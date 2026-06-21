"""
API route để bulk import thuốc/nhóm thuốc từ file Excel/CSV
"""
import io
import csv
from pathlib import Path

from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from models import db, Thuoc, NhomThuoc

# Tạo blueprint
bulk_import_bp = Blueprint('bulk_import', __name__)

# Cấu hình
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


def allowed_file(filename: str) -> bool:
    """Kiểm tra phần mở rộng file"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def read_excel_file(file_path: str) -> list[dict]:
    """Đọc file Excel (.xlsx, .xls) sử dụng pandas"""
    try:
        import pandas as pd
        df = pd.read_excel(file_path)
        return df.to_dict('records')
    except ImportError:
        raise ValueError("Thư viện pandas không được cài đặt. Vui lòng cài đặt: pip install pandas openpyxl")
    except Exception as e:
        raise ValueError(f"Lỗi khi đọc file Excel: {str(e)}")


def read_csv_file(file_obj) -> list[dict]:
    """Đọc file CSV từ file stream"""
    try:
        stream = io.TextIOWrapper(file_obj.stream, encoding='utf-8-sig', newline='')
        reader = csv.DictReader(stream)
        rows = list(reader)
        if not rows:
            raise ValueError("File CSV trống hoặc không hợp lệ")
        return rows
    except Exception as e:
        raise ValueError(f"Lỗi khi đọc file CSV: {str(e)}")


def validate_thuoc_row(row: dict, row_num: int) -> tuple[bool, str]:
    """Kiểm tra hàng dữ liệu thuốc"""
    # Xóa khoảng trắng và chuyển đổi None
    row = {k: (v.strip() if isinstance(v, str) else v) for k, v in row.items() if v is not None}
    
    # Kiểm tra trường bắt buộc
    ten_thuoc = row.get('ten_thuoc') or row.get('tên_thuốc')
    nhom_thuoc = row.get('nhom_thuoc_id') or row.get('nhóm_thuốc_id') or row.get('nhom_thuoc')
    
    if not ten_thuoc:
        return False, f"Hàng {row_num}: Thiếu tên thuốc"
    if not nhom_thuoc:
        return False, f"Hàng {row_num}: Thiếu nhóm thuốc"
    
    return True, ""


def validate_nhom_thuoc_row(row: dict, row_num: int) -> tuple[bool, str]:
    """Kiểm tra hàng dữ liệu nhóm thuốc"""
    row = {k: (v.strip() if isinstance(v, str) else v) for k, v in row.items() if v is not None}
    
    ten_nhom = row.get('ten_nhom') or row.get('tên_nhóm')
    if not ten_nhom:
        return False, f"Hàng {row_num}: Thiếu tên nhóm thuốc"
    
    return True, ""


@bulk_import_bp.route('/api/bulk-import/thuoc', methods=['POST'])
def bulk_import_thuoc():
    """
    Bulk import thuốc từ file Excel/CSV.
    
    Định dạng file:
    - Cột bắt buộc: ten_thuoc (hoặc tên_thuốc), nhom_thuoc_id (hoặc nhóm_thuốc_id)
    - Cột tùy chọn: hoat_chat, ham_luong, dang_bao_che, hang_san_xuat, 
                    nuoc_san_xuat, so_dang_ky, gia_tham_khao, don_vi_tinh, mo_ta
    
    Response:
    {
        "message": "Import thành công",
        "imported": 10,
        "skipped": 2,
        "errors": [
            {"row": 5, "message": "Nhóm thuốc không tồn tại"}
        ]
    }
    """
    # Kiểm tra file có được upload
    if 'file' not in request.files:
        return jsonify({"error": "Không tìm thấy file"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "File không được chọn"}), 400
    
    if not allowed_file(file.filename):
        return jsonify({"error": "Định dạng file không hợp lệ. Vui lòng sử dụng CSV hoặc Excel"}), 400
    
    # Kiểm tra kích thước file
    file.seek(0, 2)
    file_size = file.tell()
    file.seek(0)
    if file_size > MAX_FILE_SIZE:
        return jsonify({"error": f"File quá lớn (tối đa {MAX_FILE_SIZE // (1024*1024)}MB)"}), 400
    
    try:
        # Đọc dữ liệu từ file
        ext = file.filename.rsplit('.', 1)[1].lower()
        if ext == 'csv':
            rows = read_csv_file(file)
        else:  # xlsx hoặc xls
            # Lưu file tạm thời
            temp_path = Path(f"/tmp/{secure_filename(file.filename)}")
            file.save(str(temp_path))
            rows = read_excel_file(str(temp_path))
            # Xóa file tạm
            temp_path.unlink(missing_ok=True)
        
        if not rows:
            return jsonify({"error": "File không chứa dữ liệu"}), 400
        
        # Xử lý bulk import
        imported = 0
        skipped = 0
        errors = []
        
        for row_num, row in enumerate(rows, start=2):  # Bắt đầu từ 2 vì hàng 1 là header
            # Validate hàng
            is_valid, error_msg = validate_thuoc_row(row, row_num)
            if not is_valid:
                errors.append({"row": row_num, "message": error_msg})
                skipped += 1
                continue
            
            try:
                # Lấy giá trị từ dữ liệu (hỗ trợ cả tiếng Anh và Việt)
                ten_thuoc = (row.get('ten_thuoc') or row.get('tên_thuốc')).strip()
                nhom_thuoc_id_val = row.get('nhom_thuoc_id') or row.get('nhóm_thuốc_id') or row.get('nhom_thuoc')
                
                # Nếu nhom_thuoc_id là string, thử tìm nhóm theo tên
                if isinstance(nhom_thuoc_id_val, str):
                    nhom_thuoc_id_val = nhom_thuoc_id_val.strip()
                    # Thử chuyển sang int
                    try:
                        nhom_thuoc_id = int(nhom_thuoc_id_val)
                    except ValueError:
                        # Tìm nhóm theo tên
                        nhom = NhomThuoc.query.filter_by(ten_nhom=nhom_thuoc_id_val).first()
                        if not nhom:
                            errors.append({
                                "row": row_num,
                                "message": f"Nhóm thuốc '{nhom_thuoc_id_val}' không tồn tại"
                            })
                            skipped += 1
                            continue
                        nhom_thuoc_id = nhom.id
                else:
                    nhom_thuoc_id = int(nhom_thuoc_id_val)
                
                # Kiểm tra nhóm thuốc tồn tại
                if not NhomThuoc.query.get(nhom_thuoc_id):
                    errors.append({
                        "row": row_num,
                        "message": f"Nhóm thuốc ID {nhom_thuoc_id} không tồn tại"
                    })
                    skipped += 1
                    continue
                
                # Tạo đối tượng Thuoc
                thuoc = Thuoc(
                    ten_thuoc=ten_thuoc,
                    hoat_chat=row.get('hoat_chat') or row.get('hoạt_chất'),
                    ham_luong=row.get('ham_luong') or row.get('hàm_lượng'),
                    dang_bao_che=row.get('dang_bao_che') or row.get('dạng_bào_chế'),
                    hang_san_xuat=row.get('hang_san_xuat') or row.get('hãng_sản_xuất'),
                    nuoc_san_xuat=row.get('nuoc_san_xuat') or row.get('nước_sản_xuất'),
                    so_dang_ky=row.get('so_dang_ky') or row.get('số_đăng_ký'),
                    gia_tham_khao=float(row.get('gia_tham_khao') or row.get('giá_tham_khảo') or 0) if row.get('gia_tham_khao') or row.get('giá_tham_khảo') else None,
                    don_vi_tinh=row.get('don_vi_tinh') or row.get('đơn_vị_tính'),
                    mo_ta=row.get('mo_ta') or row.get('mô_tả'),
                    nhom_thuoc_id=nhom_thuoc_id,
                )
                
                db.session.add(thuoc)
                imported += 1
                
            except ValueError as e:
                errors.append({"row": row_num, "message": f"Lỗi dữ liệu: {str(e)}"})
                skipped += 1
            except Exception as e:
                errors.append({"row": row_num, "message": f"Lỗi xử lý: {str(e)}"})
                skipped += 1
        
        # Commit tất cả dữ liệu
        if imported > 0:
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                return jsonify({
                    "error": f"Lỗi khi lưu dữ liệu: {str(e)}",
                    "imported": imported,
                    "skipped": skipped,
                    "errors": errors
                }), 500
        
        return jsonify({
            "message": "Import thành công" if imported > 0 else "Không có dữ liệu được import",
            "imported": imported,
            "skipped": skipped,
            "errors": errors if errors else []
        }), 200
    
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Lỗi server: {str(e)}"}), 500


@bulk_import_bp.route('/api/bulk-import/nhom-thuoc', methods=['POST'])
def bulk_import_nhom_thuoc():
    """
    Bulk import nhóm thuốc từ file Excel/CSV.
    
    Định dạng file:
    - Cột bắt buộc: ten_nhom (hoặc tên_nhóm)
    - Cột tùy chọn: mo_ta (hoặc mô_tả)
    
    Response:
    {
        "message": "Import thành công",
        "imported": 5,
        "skipped": 1,
        "errors": [...]
    }
    """
    if 'file' not in request.files:
        return jsonify({"error": "Không tìm thấy file"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "File không được chọn"}), 400
    
    if not allowed_file(file.filename):
        return jsonify({"error": "Định dạng file không hợp lệ. Vui lòng sử dụng CSV hoặc Excel"}), 400
    
    # Kiểm tra kích thước file
    file.seek(0, 2)
    file_size = file.tell()
    file.seek(0)
    if file_size > MAX_FILE_SIZE:
        return jsonify({"error": f"File quá lớn (tối đa {MAX_FILE_SIZE // (1024*1024)}MB)"}), 400
    
    try:
        # Đọc dữ liệu từ file
        ext = file.filename.rsplit('.', 1)[1].lower()
        if ext == 'csv':
            rows = read_csv_file(file)
        else:  # xlsx hoặc xls
            temp_path = Path(f"/tmp/{secure_filename(file.filename)}")
            file.save(str(temp_path))
            rows = read_excel_file(str(temp_path))
            temp_path.unlink(missing_ok=True)
        
        if not rows:
            return jsonify({"error": "File không chứa dữ liệu"}), 400
        
        imported = 0
        skipped = 0
        errors = []
        
        for row_num, row in enumerate(rows, start=2):
            # Validate hàng
            is_valid, error_msg = validate_nhom_thuoc_row(row, row_num)
            if not is_valid:
                errors.append({"row": row_num, "message": error_msg})
                skipped += 1
                continue
            
            try:
                ten_nhom = (row.get('ten_nhom') or row.get('tên_nhóm')).strip()
                mo_ta = row.get('mo_ta') or row.get('mô_tả')
                
                # Kiểm tra nhóm đã tồn tại
                if NhomThuoc.query.filter_by(ten_nhom=ten_nhom).first():
                    errors.append({
                        "row": row_num,
                        "message": f"Nhóm thuốc '{ten_nhom}' đã tồn tại"
                    })
                    skipped += 1
                    continue
                
                nhom = NhomThuoc(
                    ten_nhom=ten_nhom,
                    mo_ta=mo_ta
                )
                
                db.session.add(nhom)
                imported += 1
                
            except Exception as e:
                errors.append({"row": row_num, "message": f"Lỗi: {str(e)}"})
                skipped += 1
        
        # Commit tất cả
        if imported > 0:
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                return jsonify({
                    "error": f"Lỗi khi lưu dữ liệu: {str(e)}",
                    "imported": imported,
                    "skipped": skipped,
                    "errors": errors
                }), 500
        
        return jsonify({
            "message": "Import thành công" if imported > 0 else "Không có dữ liệu được import",
            "imported": imported,
            "skipped": skipped,
            "errors": errors if errors else []
        }), 200
    
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Lỗi server: {str(e)}"}), 500


@bulk_import_bp.route('/api/bulk-import/template/thuoc', methods=['GET'])
def download_thuoc_template():
    """
    Tải file template để import thuốc (CSV)
    """
    csv_data = "ten_thuoc,nhom_thuoc_id,hoat_chat,ham_luong,dang_bao_che,hang_san_xuat,nuoc_san_xuat,so_dang_ky,gia_tham_khao,don_vi_tinh,mo_ta\n"
    csv_data += "Thuốc A,1,Hoạt chất 1,500mg,Viên nén,Hãng X,Việt Nam,123456,5000,Hộp,Mô tả thuốc A\n"
    csv_data += "Thuốc B,2,Hoạt chất 2,250mg/5ml,Siro,Hãng Y,Việt Nam,123457,3000,Lọ,Mô tả thuốc B\n"
    
    return csv_data, 200, {
        'Content-Disposition': 'attachment; filename=thuoc_template.csv',
        'Content-Type': 'text/csv; charset=utf-8'
    }


@bulk_import_bp.route('/api/bulk-import/template/nhom-thuoc', methods=['GET'])
def download_nhom_thuoc_template():
    """
    Tải file template để import nhóm thuốc (CSV)
    """
    csv_data = "ten_nhom,mo_ta\n"
    csv_data += "Thuốc kháng sinh,Dùng để điều trị nhiễm khuẩn\n"
    csv_data += "Thuốc giảm đau hạ sốt,Làm giảm đau và hạ sốt\n"
    
    return csv_data, 200, {
        'Content-Disposition': 'attachment; filename=nhom_thuoc_template.csv',
        'Content-Type': 'text/csv; charset=utf-8'
    }
