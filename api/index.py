from flask import Flask, request, jsonify, render_template_string
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
    """Xóa session cũ hơn 24 giờ"""
    data = load_data()
    current_time = time.time()
    sessions_to_delete = []
    
    for session_token, session_data in data.get("sessions", {}).items():
        if current_time - session_data.get("created_at", 0) > 86400:
            sessions_to_delete.append(session_token)
    
    for token in sessions_to_delete:
        del data["sessions"][token]
    
    if sessions_to_delete:
        save_data(data)

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
    
    session_token = generate_session_token()
    user_ip = request.remote_addr
    user_agent = request.headers.get('User-Agent', 'Unknown')
    
    # URL đích là trang success với token
    destination_url = f"https://webkeyy.vercel.app/success?token={session_token}"
    
    try:
        create_url = f"{LINK4M_API}?api={LINK4M_KEY}&url={destination_url}"
        res = requests.get(create_url, timeout=10).json()
        
        if res.get("status") != "success" or not res.get("shortenedUrl"):
            return jsonify({"status": "error", "msg": "Không tạo được link rút gọn"})
        
        short_url = res["shortenedUrl"]
        
        # Lưu session NHƯNG CHƯA TẠO KEY
        data = load_data()
        data["sessions"][session_token] = {
            "unique_key": None,  # Chưa có key
            "created_at": time.time(),
            "verified": False,  # Chưa vượt link
            "owner_ip": user_ip,
            "owner_user_agent": user_agent
        }
        save_data(data)
        
        return jsonify({
            "status": "ok",
            "message": "Vui lòng vượt link để nhận key",
            "url": short_url,
            "token": session_token
        })
    except Exception as e:
        return jsonify({"status": "error", "msg": f"Lỗi: {str(e)}"})

@app.route("/success")
def success_page():
    """Trang đích sau khi vượt Link4m - TỰ ĐỘNG TẠO VÀ HIỂN THỊ KEY"""
    session_token = request.args.get("token")
    
    if not session_token:
        return render_template_string(ERROR_PAGE, error_msg="Thiếu token")
    
    data = load_data()
    
    if session_token not in data.get("sessions", {}):
        return render_template_string(ERROR_PAGE, error_msg="Session không tồn tại hoặc đã hết hạn")
    
    session = data["sessions"][session_token]
    current_time = time.time()
    created_at = session.get("created_at", 0)
    
    # Kiểm tra hết hạn
    if current_time - created_at > 86400:
        del data["sessions"][session_token]
        save_data(data)
        return render_template_string(ERROR_PAGE, error_msg="Session đã hết hạn (quá 24 giờ)")
    
    # Lấy IP hiện tại
    current_ip = request.remote_addr
    owner_ip = session.get("owner_ip")
    
    # Kiểm tra IP - CHẶN SHARE KEY
    if owner_ip and current_ip != owner_ip:
        return render_template_string(ERROR_PAGE, 
            error_msg="Key này không phải của bạn! Vui lòng vào https://webkeyy.vercel.app để lấy key riêng.")
    
    # TẠO KEY NẾU CHƯA CÓ (lần đầu vào trang success)
    if not session.get("unique_key"):
        session["unique_key"] = generate_key()
        session["verified"] = True
        data["sessions"][session_token] = session
        save_data(data)
    
    unique_key = session["unique_key"]
    expire_time = created_at + 86400
    expire_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expire_time))
    
    return render_template_string(SUCCESS_PAGE, 
        key=unique_key, 
        expire_at=expire_str)

@app.route("/api/check_key")
def check_key():
    """Kiểm tra key có hợp lệ không - CHẶN SHARE KEY"""
    key = request.args.get("key")
    
    if not key:
        return jsonify({"status": "fail", "msg": "Thiếu key"})
    
    current_ip = request.remote_addr
    data = load_data()
    current_time = time.time()
    
    for session_token, session_data in data.get("sessions", {}).items():
        if session_data.get("unique_key") == key:
            created_at = session_data.get("created_at", 0)
            
            # Kiểm tra hết hạn
            if current_time - created_at > 86400:
                del data["sessions"][session_token]
                save_data(data)
                return jsonify({"status": "fail", "msg": "Key đã hết hạn (quá 24 giờ)"})
            
            # Kiểm tra IP
            owner_ip = session_data.get("owner_ip")
            if owner_ip and current_ip != owner_ip:
                return jsonify({
                    "status": "fail",
                    "msg": "Key này không phải của bạn! Vui lòng vào https://webkeyy.vercel.app để lấy key riêng."
                })
            
            # Key hợp lệ
            expire_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(created_at + 86400))
            return jsonify({
                "status": "ok",
                "msg": "Key hợp lệ",
                "expire_at": expire_at,
                "is_unique": True
            })
    
    return jsonify({"status": "fail", "msg": "Key không tồn tại hoặc không hợp lệ"})

# HTML TEMPLATE CHO TRANG SUCCESS
SUCCESS_PAGE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎉 Key Của Bạn - ARES Tool</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%);
            color: #fff;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            max-width: 600px;
            width: 100%;
        }
        .success-box {
            background: rgba(255, 255, 255, 0.05);
            border: 2px solid #00ff9d;
            border-radius: 20px;
            padding: 40px;
            text-align: center;
            box-shadow: 0 0 40px rgba(0, 255, 157, 0.3);
            animation: fadeIn 0.5s ease-in;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .title {
            font-size: 48px;
            color: #00ff9d;
            margin-bottom: 10px;
            text-shadow: 0 0 20px rgba(0, 255, 157, 0.5);
        }
        .subtitle {
            font-size: 24px;
            color: #ffc107;
            margin-bottom: 30px;
        }
        .key-container {
            background: rgba(0, 0, 0, 0.3);
            border: 2px solid #00ff9d;
            border-radius: 15px;
            padding: 30px;
            margin: 30px 0;
        }
        .key-label {
            font-size: 18px;
            color: #00ff9d;
            margin-bottom: 15px;
        }
        .key-value {
            font-size: 22px;
            font-family: 'Courier New', monospace;
            color: #fff;
            background: rgba(0, 255, 157, 0.1);
            padding: 15px;
            border-radius: 10px;
            word-break: break-all;
            margin-bottom: 15px;
        }
        .copy-btn {
            background: #00ff9d;
            color: #0a0e27;
            border: none;
            padding: 12px 30px;
            font-size: 16px;
            font-weight: bold;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .copy-btn:hover {
            background: #00cc7d;
            transform: scale(1.05);
        }
        .copy-btn:active {
            transform: scale(0.95);
        }
        .info {
            background: rgba(255, 193, 7, 0.1);
            border: 1px solid #ffc107;
            border-radius: 10px;
            padding: 20px;
            margin-top: 20px;
        }
        .info-item {
            margin: 10px 0;
            font-size: 16px;
        }
        .info-label {
            color: #ffc107;
            font-weight: bold;
        }
        .back-btn {
            display: inline-block;
            margin-top: 20px;
            padding: 12px 30px;
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid #00ff9d;
            border-radius: 10px;
            color: #00ff9d;
            text-decoration: none;
            transition: all 0.3s;
        }
        .back-btn:hover {
            background: rgba(0, 255, 157, 0.2);
        }
        .toast {
            position: fixed;
            top: 20px;
            right: 20px;
            background: #00ff9d;
            color: #0a0e27;
            padding: 15px 25px;
            border-radius: 10px;
            font-weight: bold;
            display: none;
            animation: slideIn 0.3s ease-in;
        }
        @keyframes slideIn {
            from { transform: translateX(400px); }
            to { transform: translateX(0); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="success-box">
            <div class="title">🎉</div>
            <div class="subtitle">Chúc Mừng!</div>
            <p style="font-size: 18px; margin-bottom: 20px;">
                Bạn đã vượt link thành công!<br>
                Đây là key riêng của bạn:
            </p>
            
            <div class="key-container">
                <div class="key-label">🔑 KEY CỦA BẠN:</div>
                <div class="key-value" id="keyValue">{{ key }}</div>
                <button class="copy-btn" onclick="copyKey()">📋 Copy Key</button>
            </div>
            
            <div class="info">
                <div class="info-item">
                    <span class="info-label">⏰ Hết hạn:</span> {{ expire_at }}
                </div>
                <div class="info-item">
                    <span class="info-label">⚠️ Lưu ý:</span> Key chỉ sử dụng được trên thiết bị này
                </div>
                <div class="info-item">
                    <span class="info-label">🔒 Bảo mật:</span> Không chia sẻ key cho người khác
                </div>
            </div>
            
            <a href="/" class="back-btn">🏠 Về Trang Chủ</a>
        </div>
    </div>
    
    <div class="toast" id="toast">✅ Đã copy key vào clipboard!</div>
    
    <script>
        function copyKey() {
            const keyValue = document.getElementById('keyValue').innerText;
            navigator.clipboard.writeText(keyValue).then(() => {
                showToast();
            });
        }
        
        function showToast() {
            const toast = document.getElementById('toast');
            toast.style.display = 'block';
            setTimeout(() => {
                toast.style.display = 'none';
            }, 3000);
        }
    </script>
</body>
</html>
"""

# HTML TEMPLATE CHO TRANG LỖI
ERROR_PAGE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>❌ Lỗi - ARES Tool</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%);
            color: #fff;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .error-box {
            background: rgba(255, 255, 255, 0.05);
            border: 2px solid #ff4444;
            border-radius: 20px;
            padding: 40px;
            text-align: center;
            max-width: 500px;
        }
        .error-icon {
            font-size: 64px;
            margin-bottom: 20px;
        }
        .error-title {
            font-size: 28px;
            color: #ff4444;
            margin-bottom: 20px;
        }
        .error-msg {
            font-size: 18px;
            margin-bottom: 30px;
            line-height: 1.6;
        }
        .back-btn {
            display: inline-block;
            padding: 12px 30px;
            background: #00ff9d;
            color: #0a0e27;
            border-radius: 10px;
            text-decoration: none;
            font-weight: bold;
            transition: all 0.3s;
        }
        .back-btn:hover {
            background: #00cc7d;
            transform: scale(1.05);
        }
    </style>
</head>
<body>
    <div class="error-box">
        <div class="error-icon">❌</div>
        <div class="error-title">Có Lỗi Xảy Ra</div>
        <div class="error-msg">{{ error_msg }}</div>
        <a href="/" class="back-btn">🏠 Về Trang Chủ</a>
    </div>
</body>
</html>
"""
