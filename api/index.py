from flask import Flask, request, jsonify
import json
import os
import time
import random
import string
import secrets
import requests

app = Flask(__name__)

LINK4M_API = "https://link4m.co/api-shorten/v2"
LINK4M_KEY = os.getenv("LINK4M_KEY")

KEY_FILE = "/tmp/key.json"

def generate_key(length=24):
    """Tạo key ngẫu nhiên"""
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

def generate_session_token():
    """Tạo session token"""
    return secrets.token_urlsafe(32)

def load_data():
    """Load dữ liệu từ file"""
    if not os.path.exists(KEY_FILE):
        return {"sessions": {}}
    try:
        with open(KEY_FILE, "r") as f:
            data = json.load(f)
            if "sessions" not in data:
                data["sessions"] = {}
            return data
    except:
        return {"sessions": {}}

def save_data(data):
    """Lưu dữ liệu vào file"""
    with open(KEY_FILE, "w") as f:
        json.dump(data, f, indent=2)

def cleanup_old_sessions():
    """Xóa session cũ hơn 24 giờ - TỰ ĐỘNG"""
    data = load_data()
    current_time = time.time()
    sessions_to_delete = []
    
    for session_token, session_data in data.get("sessions", {}).items():
        if current_time - session_data.get("created_at", 0) > 86400:  # 24 giờ
            sessions_to_delete.append(session_token)
    
    for token in sessions_to_delete:
        del data["sessions"][token]
    
    if sessions_to_delete:
        save_data(data)
        print(f"[CLEANUP] Đã xóa {len(sessions_to_delete)} session hết hạn")

# ✅ TỰ ĐỘNG CLEANUP MỖI KHI CÓ REQUEST
@app.before_request
def auto_cleanup():
    """Tự động cleanup trước mỗi request"""
    cleanup_old_sessions()

@app.route("/")
def home():
    """Trang chủ"""
    try:
        with open('folder/index.html', 'r', encoding='utf-8') as f:
            return f.read()
    except:
        return "index.html not found"

@app.route("/api/get_link")
def get_link():
    """Tạo link rút gọn Link4m"""
    if not LINK4M_KEY:
        return jsonify({"status": "error", "msg": "Chưa cấu hình LINK4M_KEY"})
    
    # Tạo session token và key riêng
    session_token = generate_session_token()
    unique_key = generate_key()
    
    # Tạo URL giả (Link4m không redirect được nên không cần URL thật)
    destination_url = "https://webkeyy.vercel.app"
    
    try:
        # Tạo link rút gọn Link4m
        create_url = f"{LINK4M_API}?api={LINK4M_KEY}&url={destination_url}"
        res = requests.get(create_url, timeout=10).json()
        
        if res.get("status") != "success" or not res.get("shortenedUrl"):
            return jsonify({"status": "error", "msg": "Không tạo được link rút gọn"})
        
        short_url = res["shortenedUrl"]
        
        # Lưu session với KEY RIÊNG
        data = load_data()
        data["sessions"][session_token] = {
            "unique_key": unique_key,
            "created_at": time.time(),
            "link_clicked": False,
            "ip_address": request.remote_addr
        }
        save_data(data)
        
        return jsonify({
            "status": "ok",
            "message": "Vui lòng vượt link và đợi 15 giây",
            "url": short_url,
            "token": session_token
        })
    except Exception as e:
        return jsonify({"status": "error", "msg": f"Lỗi: {str(e)}"})

@app.route("/api/get_key")
def get_key():
    """Lấy KEY sau khi đã đợi đủ thời gian"""
    session_token = request.args.get("token")
    
    if not session_token:
        return jsonify({"status": "error", "msg": "Thiếu token"})
    
    data = load_data()
    
    if session_token not in data.get("sessions", {}):
        return jsonify({"status": "error", "msg": "Session không tồn tại hoặc đã hết hạn"})
    
    session = data["sessions"][session_token]
    created_at = session.get("created_at", 0)
    current_time = time.time()
    
    # ✅ KIỂM TRA HẾT HẠN
    if current_time - created_at > 86400:
        # Xóa session hết hạn ngay
        del data["sessions"][session_token]
        save_data(data)
        return jsonify({"status": "error", "msg": "Session đã hết hạn (quá 24 giờ)"})
    # KIỂM TRA: Phải đợi ít nhất 60 giây
    time_elapsed = current_time - created_at
    if time_elapsed < 60:
    return jsonify({
        "status": "error",
        "msg": "Vui lòng vượt link"
    })
    
    # Đủ thời gian → Cho phép lấy key
    unique_key = session.get("unique_key")
    expire_time = created_at + 86400
    
    if not unique_key:
        return jsonify({"status": "error", "msg": "Key không tồn tại"})
    
    # Đánh dấu đã lấy key
    data["sessions"][session_token]["link_clicked"] = True
    save_data(data)
    
    return jsonify({
        "status": "ok",
        "key": unique_key,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(created_at)),
        "expire_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expire_time)),
        "is_unique": True
    })

@app.route("/api/check_key")
def check_key():
    """Kiểm tra key có hợp lệ không - Tối đa 3 IP"""
    key = request.args.get("key")
    
    if not key:
        return jsonify({"status": "fail", "msg": "Thiếu key"})
    
    data = load_data()
    current_time = time.time()
    
    # Lấy IP thật từ header (Vercel forward IP qua X-Forwarded-For)
    current_ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
    
    # Tìm key trong tất cả sessions
    for session_token, session_data in data.get("sessions", {}).items():
        if session_data.get("unique_key") == key:
            created_at = session_data.get("created_at", 0)
            
            # ✅ KIỂM TRA HẾT HẠN
            if current_time - created_at > 86400:
                del data["sessions"][session_token]
                save_data(data)
                return jsonify({"status": "fail", "msg": "Key đã hết hạn (quá 24 giờ)"})
            
            # ✅ KIỂM TRA IP - TỐI ĐA 3 IP
            ip_list = session_data.get("ip_list", [])
            max_ips = 3  # Tối đa 3 IP
            
            if current_ip not in ip_list:
                # IP mới - kiểm tra đã đủ 3 IP chưa
                if len(ip_list) >= max_ips:
                    return jsonify({
                        "status": "fail",
                        "msg": f"Key đã đạt giới hạn {max_ips} IP. Vui lòng lấy key mới."
                    })
                
                # Thêm IP mới vào danh sách
                ip_list.append(current_ip)
                data["sessions"][session_token]["ip_list"] = ip_list
                save_data(data)
            
            # Key hợp lệ
            expire_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(created_at + 86400))
            return jsonify({
                "status": "ok",
                "msg": "Key hợp lệ",
                "date": expire_at,
                "expire_at": expire_at,
                "is_unique": True
            })
    
    # Không tìm thấy key
    return jsonify({"status": "fail", "msg": "Key không tồn tại hoặc không hợp lệ"})
    
    # Không tìm thấy key
    return jsonify({"status": "fail", "msg": "Key không tồn tại hoặc không hợp lệ"})
