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

def get_base_url():
    base_url = os.getenv("BASE_URL", "")
    if base_url:
        return base_url if base_url.startswith("http") else f"https://{base_url}"
    
    if request:
        return request.url_root.rstrip('/')
    
    return ""

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
    """Xóa session cũ hơn 24 giờ"""
    data = load_data()
    current_time = time.time()
    sessions_to_delete = []
    
    for session_token, session_data in data.get("sessions", {}).items():
        # Xóa session cũ hơn 24 giờ
        if current_time - session_data.get("created_at", 0) > 86400:  # 24 giờ
            sessions_to_delete.append(session_token)
    
    for token in sessions_to_delete:
        del data["sessions"][token]
    
    if sessions_to_delete:
        save_data(data)

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
    """Tạo link rút gọn - MỖI SESSION MỘT KEY RIÊNG"""
    cleanup_old_sessions()
    
    if not LINK4M_KEY:
        return jsonify({"status": "error", "msg": "Chưa cấu hình LINK4M_KEY"})
    
    # Tạo session token và key riêng cho user này
    session_token = generate_session_token()
    verify_secret = generate_session_token()
    unique_key = generate_key()  # KEY RIÊNG cho session này
    
    base_url = get_base_url()
    if not base_url:
        return jsonify({"status": "error", "msg": "Không xác định được BASE_URL"})
    
    destination = f"{base_url}/api/verify?token={session_token}&secret={verify_secret}"
    
    try:
        # Tạo link rút gọn
        create_url = f"{LINK4M_API}?api={LINK4M_KEY}&url={destination}"
        res = requests.get(create_url, timeout=10).json()
        
        if res.get("status") != "success" or not res.get("shortenedUrl"):
            return jsonify({"status": "error", "msg": "Không tạo được link rút gọn"})
        
        short_url = res["shortenedUrl"]
        
        # Lưu session với KEY RIÊNG
        data = load_data()
        data["sessions"][session_token] = {
            "verified": False,
            "verify_secret": verify_secret,
            "created_at": time.time(),
            "unique_key": unique_key,  # KEY RIÊNG - QUAN TRỌNG!
            "ip_address": request.remote_addr  # Track IP (optional)
        }
        save_data(data)
        
        return jsonify({
            "status": "ok",
            "message": "Vui lòng vượt link để lấy key RIÊNG của bạn",
            "url": short_url,
            "token": session_token
        })
    except Exception as e:
        return jsonify({"status": "error", "msg": f"Lỗi: {str(e)}"})

@app.route("/api/verify")
def verify():
    """Xác thực sau khi vượt link"""
    session_token = request.args.get("token")
    verify_secret = request.args.get("secret")
    
    if not session_token or not verify_secret:
        return "❌ Thiếu thông tin xác thực"
    
    data = load_data()
    
    if session_token not in data.get("sessions", {}):
        return "❌ Session không tồn tại hoặc đã hết hạn"
    
    session = data["sessions"][session_token]
    
    if session.get("verify_secret") != verify_secret:
        return "❌ Secret không hợp lệ"
    
    # Đánh dấu đã verify
    data["sessions"][session_token]["verified"] = True
    data["sessions"][session_token]["verified_at"] = time.time()
    save_data(data)
    
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Xác thực thành công</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                margin: 0;
            }
            .success-box {
                background: white;
                padding: 40px;
                border-radius: 15px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                text-align: center;
                max-width: 400px;
            }
            .checkmark {
                font-size: 80px;
                color: #4CAF50;
                animation: pop 0.5s ease-out;
            }
            @keyframes pop {
                0% { transform: scale(0); }
                50% { transform: scale(1.2); }
                100% { transform: scale(1); }
            }
            h1 { color: #333; margin: 20px 0; }
            p { color: #666; font-size: 16px; line-height: 1.6; }
            .btn {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 12px 30px;
                border-radius: 25px;
                font-size: 16px;
                cursor: pointer;
                margin-top: 20px;
                text-decoration: none;
                display: inline-block;
            }
            .warning {
                background: #fff3cd;
                color: #856404;
                padding: 15px;
                border-radius: 10px;
                margin: 15px 0;
                font-size: 14px;
            }
        </style>
    </head>
    <body>
        <div class="success-box">
            <div class="checkmark">✅</div>
            <h1>Xác thực thành công!</h1>
            <p>Bạn đã vượt link thành công.</p>
            <div class="warning">
                <strong>⚠️ LƯU Ý:</strong><br>
                Hãy ĐÓNG TAB NÀY và quay lại trang chủ để nhấn "Lấy Key".<br>
                Key của bạn là RIÊNG, không chia sẻ cho người khác!
            </div>
            <a href="/" class="btn">Quay lại trang chủ</a>
        </div>
    </body>
    </html>
    """

@app.route("/api/get_key")
def get_key():
    """Lấy KEY RIÊNG sau khi đã verify"""
    session_token = request.args.get("token")
    
    if not session_token:
        return jsonify({"status": "error", "msg": "Thiếu token"})
    
    data = load_data()
    
    if session_token not in data.get("sessions", {}):
        return jsonify({"status": "error", "msg": "Session không tồn tại hoặc đã hết hạn"})
    
    session = data["sessions"][session_token]
    
    if not session.get("verified"):
        return jsonify({"status": "error", "msg": "Bạn chưa vượt link. Vui lòng vượt link trước!"})
    
    # Trả về KEY RIÊNG của session này
    unique_key = session.get("unique_key")
    created_at = session.get("created_at", time.time())
    
    if not unique_key:
        return jsonify({"status": "error", "msg": "Key không tồn tại"})
    
    # Tính thời gian hết hạn
    expire_time = created_at + 86400  # 24 giờ
    
    return jsonify({
        "status": "ok",
        "key": unique_key,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(created_at)),
        "expire_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expire_time)),
        "is_unique": True  # Đánh dấu là key riêng
    })

@app.route("/api/check_key")
def check_key():
    """Kiểm tra key có hợp lệ không - CHỈ KEY RIÊNG MỚI HỢP LỆ"""
    key = request.args.get("key")
    
    if not key:
        return jsonify({"status": "fail", "msg": "Thiếu key"})
    
    data = load_data()
    current_time = time.time()
    
    # Tìm key trong tất cả sessions
    for session_token, session_data in data.get("sessions", {}).items():
        if session_data.get("unique_key") == key:
            # Kiểm tra key đã verify chưa
            if not session_data.get("verified"):
                return jsonify({"status": "fail", "msg": "Key chưa được xác thực"})
            
            # Kiểm tra key còn hạn không (24 giờ)
            created_at = session_data.get("created_at", 0)
            if current_time - created_at > 86400:
                return jsonify({"status": "fail", "msg": "Key đã hết hạn (quá 24 giờ)"})
            
            # Key hợp lệ
            expire_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(created_at + 86400))
            return jsonify({
                "status": "ok",
                "msg": "Key hợp lệ",
                "expire_at": expire_at,
                "is_unique": True
            })
    
    # Không tìm thấy key
    return jsonify({"status": "fail", "msg": "Key không tồn tại hoặc không hợp lệ"})
