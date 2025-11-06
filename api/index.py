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

@app.route("/huong-dan")
def huong_dan():
    """Trang hướng dẫn cài đặt tool - ARES Theme"""
    return render_template_string(HUONG_DAN_HTML)

# HTML TEMPLATE CHO TRANG HƯỚNG DẪN
HUONG_DAN_HTML = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hướng Dẫn - ARES Tool</title>
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
            padding: 20px;
        }

        .container {
            max-width: 900px;
            margin: 0 auto;
            padding-top: 20px;
        }

        .header {
            text-align: center;
            margin-bottom: 40px;
        }

        .logo {
            font-size: 72px;
            font-weight: bold;
            color: #00ff9d;
            text-shadow: 0 0 30px rgba(0, 255, 157, 0.5);
            letter-spacing: 8px;
            margin-bottom: 10px;
        }

        .subtitle {
            font-size: 20px;
            color: #ffc107;
            margin-bottom: 10px;
        }

        .description {
            font-size: 16px;
            color: rgba(255, 255, 255, 0.7);
            max-width: 600px;
            margin: 0 auto;
        }

        .content-box {
            background: rgba(255, 255, 255, 0.05);
            border: 2px solid rgba(0, 255, 157, 0.3);
            border-radius: 20px;
            padding: 40px;
            margin-bottom: 30px;
        }

        h2 {
            font-size: 24px;
            color: #00ff9d;
            margin-top: 30px;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        h2:first-child {
            margin-top: 0;
        }

        .step-number {
            background: #00ff9d;
            color: #0a0e27;
            width: 35px;
            height: 35px;
            border-radius: 50%;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
            font-weight: bold;
        }

        p, li {
            font-size: 16px;
            color: rgba(255, 255, 255, 0.85);
            line-height: 1.8;
            margin-bottom: 15px;
        }

        .intro-text {
            font-size: 17px;
            color: rgba(255, 255, 255, 0.9);
            line-height: 1.8;
            margin-bottom: 25px;
            padding: 20px;
            background: rgba(0, 255, 157, 0.1);
            border-left: 4px solid #00ff9d;
            border-radius: 8px;
        }

        .code-block {
            position: relative;
            background: #1e293b;
            border: 1px solid rgba(0, 255, 157, 0.2);
            color: #e2e8f0;
            padding: 20px;
            padding-right: 80px;
            border-radius: 12px;
            margin: 20px 0;
            font-family: 'Courier New', Courier, monospace;
            font-size: 15px;
            overflow-x: auto;
            box-shadow: 0 0 20px rgba(0, 255, 157, 0.1);
        }

        .copy-btn {
            position: absolute;
            top: 12px;
            right: 12px;
            background: #00ff9d;
            color: #0a0e27;
            border: none;
            padding: 8px 16px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 13px;
            font-weight: bold;
            transition: all 0.3s;
        }

        .copy-btn:hover {
            background: #00cc7d;
            transform: scale(1.05);
        }

        .copy-btn:active {
            transform: scale(0.95);
        }

        .error-box {
            background: rgba(255, 68, 68, 0.1);
            border: 2px solid #ff4444;
            border-radius: 15px;
            padding: 25px;
            margin: 25px 0;
        }

        .error-title {
            color: #ff4444;
            font-weight: 700;
            font-size: 18px;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .error-text {
            color: rgba(255, 255, 255, 0.85);
            font-size: 16px;
            line-height: 1.7;
            margin-bottom: 12px;
        }

        .solution {
            color: #ffc107;
            font-weight: 600;
            margin-top: 15px;
            margin-bottom: 8px;
            font-size: 16px;
        }

        .link {
            color: #00ff9d;
            text-decoration: none;
            font-weight: 600;
            border-bottom: 2px solid transparent;
            transition: border-color 0.3s;
        }

        .link:hover {
            border-bottom-color: #00ff9d;
        }

        ol {
            margin-left: 25px;
            margin-bottom: 20px;
        }

        ol li {
            margin-bottom: 12px;
            padding-left: 5px;
        }

        .highlight-box {
            background: rgba(255, 193, 7, 0.1);
            border: 2px solid #ffc107;
            border-radius: 15px;
            padding: 25px;
            margin: 25px 0;
        }

        .highlight-box h3 {
            color: #ffc107;
            font-size: 20px;
            margin-bottom: 15px;
        }

        .note-list {
            list-style: none;
            margin-left: 0;
        }

        .note-list li {
            padding-left: 30px;
            position: relative;
            margin-bottom: 10px;
        }

        .note-list li:before {
            content: "•";
            color: #ffc107;
            font-size: 24px;
            position: absolute;
            left: 0;
            top: -3px;
        }

        .back-btn {
            display: inline-block;
            margin-top: 30px;
            padding: 15px 35px;
            background: linear-gradient(135deg, #00ff9d 0%, #00cc7d 100%);
            color: #0a0e27;
            text-decoration: none;
            border-radius: 12px;
            font-weight: 700;
            font-size: 16px;
            transition: all 0.3s;
            box-shadow: 0 0 20px rgba(0, 255, 157, 0.3);
        }

        .back-btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 30px rgba(0, 255, 157, 0.4);
        }

        .toast {
            position: fixed;
            top: 20px;
            right: 20px;
            background: #00ff9d;
            color: #0a0e27;
            padding: 15px 25px;
            border-radius: 12px;
            font-weight: 700;
            display: none;
            box-shadow: 0 4px 20px rgba(0, 255, 157, 0.4);
            z-index: 1000;
            animation: slideIn 0.3s ease-out;
        }

        @keyframes slideIn {
            from {
                transform: translateX(400px);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }

        .divider {
            height: 2px;
            background: linear-gradient(90deg, transparent, #00ff9d, transparent);
            margin: 40px 0;
        }

        @media (max-width: 768px) {
            .logo {
                font-size: 48px;
            }
            .subtitle {
                font-size: 16px;
            }
            .content-box {
                padding: 25px;
            }
            h2 {
                font-size: 20px;
            }
            .code-block {
                font-size: 13px;
                padding-right: 20px;
            }
            .copy-btn {
                position: static;
                display: block;
                width: 100%;
                margin-top: 15px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">ARES</div>
            <div class="subtitle">HƯỚNG DẪN CÀI ĐẶT VÀ SỬ DỤNG TOOL</div>
            <div class="description">
                Hướng dẫn chi tiết cách cài đặt và chạy ARES Tool trên Android (Termux)
            </div>
        </div>

        <div class="content-box">
            <div class="intro-text">
                💡 <strong>Lưu ý:</strong> ARES Tool yêu cầu license key miễn phí để sử dụng. 
                Key có hiệu lực 24 giờ và chỉ hoạt động trên thiết bị đã lấy key.
            </div>

            <h2><span class="step-number">1</span> Giới thiệu</h2>
            <p>
                ARES Tool là công cụ tự động hóa với hệ thống key bảo mật. Termux là trình giả lập 
                terminal cho Android, cho phép bạn chạy các lệnh Linux trên điện thoại.
            </p>

            <div class="divider"></div>

            <h2><span class="step-number">2</span> Cài đặt Termux</h2>
            <p>
                Tải Termux từ <strong>F-Droid</strong> (không dùng Google Play Store vì đã lỗi thời):
            </p>
            <p>
                <a href="https://f-droid.org/en/packages/com.termux/" class="link" target="_blank">
                    → Tải Termux từ F-Droid
                </a>
            </p>

            <div class="divider"></div>

            <h2><span class="step-number">3</span> Cập nhật hệ thống</h2>
            <p>Mở Termux và chạy lệnh:</p>
            <div class="code-block">
                <button class="copy-btn" onclick="copyCode(this, 'pkg update && pkg upgrade -y')">Copy</button>
                <code>pkg update && pkg upgrade -y</code>
            </div>

            <h2><span class="step-number">4</span> Cài đặt Python và Git</h2>
            <div class="code-block">
                <button class="copy-btn" onclick="copyCode(this, 'pkg install python git -y')">Copy</button>
                <code>pkg install python git -y</code>
            </div>

            <h2><span class="step-number">5</span> Tải tool từ GitHub</h2>
            <div class="code-block">
                <button class="copy-btn" onclick="copyCode(this, 'git clone https://github.com/quocdung1303/arestool.git')">Copy</button>
                <code>git clone https://github.com/quocdung1303/arestool.git</code>
            </div>

            <h2><span class="step-number">6</span> Vào thư mục tool</h2>
            <div class="code-block">
                <button class="copy-btn" onclick="copyCode(this, 'cd arestool')">Copy</button>
                <code>cd arestool</code>
            </div>

            <h2><span class="step-number">7</span> Cài đặt thư viện</h2>
            <div class="code-block">
                <button class="copy-btn" onclick="copyCode(this, 'pip install -r requirements.txt')">Copy</button>
                <code>pip install -r requirements.txt</code>
            </div>

            <div class="divider"></div>

            <h2><span class="step-number">8</span> Lấy License Key</h2>
            <div class="highlight-box">
                <h3>🔑 Hướng dẫn lấy key:</h3>
                <ol>
                    <li>Truy cập: <a href="https://webkeyy.vercel.app" class="link" target="_blank">https://webkeyy.vercel.app</a></li>
                    <li>Click nút <strong>"Lấy Key Ngay"</strong></li>
                    <li>Vượt link quảng cáo Link4m</li>
                    <li>Sau khi vượt xong → Tự động hiển thị key</li>
                    <li>Copy key để sử dụng</li>
                </ol>
            </div>

            <div class="divider"></div>

            <h2><span class="step-number">9</span> Chạy tool</h2>
            <div class="code-block">
                <button class="copy-btn" onclick="copyCode(this, 'python obf-botcucvip.py')">Copy</button>
                <code>python obf-botcucvip.py</code>
            </div>
            <p>Tool sẽ yêu cầu nhập license key. Paste key đã lấy ở bước 8.</p>

            <div class="divider"></div>

            <h2>⚠️ Lỗi thường gặp</h2>

            <div class="error-box">
                <div class="error-title">❌ Lỗi: command not found: git</div>
                <div class="error-text">
                    Git chưa được cài đặt trong Termux.
                </div>
                <div class="solution">✅ Cách khắc phục:</div>
                <div class="code-block">
                    <button class="copy-btn" onclick="copyCode(this, 'pkg install git -y')">Copy</button>
                    <code>pkg install git -y</code>
                </div>
            </div>

            <div class="error-box">
                <div class="error-title">❌ Lỗi: No module named 'requests'</div>
                <div class="error-text">
                    Thư viện chưa được cài đặt đầy đủ.
                </div>
                <div class="solution">✅ Cách khắc phục:</div>
                <div class="code-block">
                    <button class="copy-btn" onclick="copyCode(this, 'pip install requests colorama websocket-client')">Copy</button>
                    <code>pip install requests colorama websocket-client</code>
                </div>
            </div>

            <div class="error-box">
                <div class="error-title">❌ Lỗi: License key không hợp lệ</div>
                <div class="error-text">
                    Key đã hết hạn (quá 24 giờ) hoặc đang được sử dụng trên thiết bị khác.
                </div>
                <div class="solution">✅ Cách khắc phục:</div>
                <div class="error-text">
                    Lấy key mới tại <a href="https://webkeyy.vercel.app" class="link" target="_blank">webkeyy.vercel.app</a>
                </div>
            </div>

            <div class="divider"></div>

            <div class="highlight-box">
                <h3>📌 Lưu ý quan trọng:</h3>
                <ul class="note-list">
                    <li>Key có hiệu lực <strong>24 giờ</strong></li>
                    <li>Key chỉ hoạt động trên <strong>thiết bị đã lấy</strong></li>
                    <li><strong>Không chia sẻ</strong> key cho người khác</li>
                    <li>Lấy key mới mỗi 24 giờ tại <a href="https://webkeyy.vercel.app" class="link">webkeyy.vercel.app</a></li>
                </ul>
            </div>

            <div style="text-align: center;">
                <a href="/" class="back-btn">← Về Trang Chủ Lấy Key</a>
            </div>
        </div>
    </div>

    <div class="toast" id="toast">✅ Đã copy vào clipboard!</div>

    <script>
        function copyCode(button, text) {
            navigator.clipboard.writeText(text).then(() => {
                showToast();
                button.textContent = 'Copied!';
                button.style.background = '#ffc107';
                setTimeout(() => {
                    button.textContent = 'Copy';
                    button.style.background = '#00ff9d';
                }, 2000);
            }).catch(() => {
                alert('Không thể copy. Vui lòng copy thủ công.');
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
