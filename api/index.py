from flask import Flask, request, jsonify, render_template_string
import json
import os
import time
import random
import string
import secrets
import requests
from collections import defaultdict, deque

app = Flask(__name__)

LINK4M_KEY = os.getenv("LINK4M_KEY")
KEY_FILE = "/tmp/key.json"

# Rate limiting storage (in-memory)
rate_limit_storage = defaultdict(lambda: deque(maxlen=100))

def generate_key(length=24):
    """Tạo key ngẫu nhiên"""
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

def generate_session_token():
    """Tạo session token"""
    return secrets.token_urlsafe(32)

def check_rate_limit(identifier, max_requests=10, time_window=60):
    """Check rate limit cho một identifier (key hoặc IP)"""
    current_time = time.time()
    request_times = rate_limit_storage[identifier]
    
    while request_times and current_time - request_times[0] > time_window:
        request_times.popleft()
    
    if len(request_times) >= max_requests:
        return False, len(request_times)
    
    request_times.append(current_time)
    return True, len(request_times)

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
        print(f"[CLEANUP] Đã xóa {len(sessions_to_delete)} sessions hết hạn")

@app.before_request
def auto_cleanup():
    """Tự động cleanup trước mỗi request"""
    cleanup_old_sessions()

# ==================== ROUTES ====================

@app.route("/")
def home():
    """Trang chủ - Chỉ hướng dẫn sử dụng tool"""
    return render_template_string(HOME_HTML)

@app.route("/api/get_link")
def get_link():
    """API cho TOOL - Tạo link rút gọn Link4m"""
    if not LINK4M_KEY:
        return jsonify({"status": "error", "msg": "Chưa cấu hình LINK4M_KEY"})
    
    session_token = generate_session_token()
    unique_key = generate_key()
    user_ip = request.remote_addr
    user_agent = request.headers.get('User-Agent', 'Unknown')
    
    # URL đích - Route hiển thị key
    destination_url = f"https://reskey.vercel.app/k/{session_token}"
    
    try:
        # Gọi API Link4m
        api_url = f"https://link4m.co/api?api={LINK4M_KEY}&url={destination_url}"
        
        print(f"[INFO] Gọi Link4m API")
        
        response = requests.get(api_url, timeout=10)
        short_url = response.text.strip()
        
        # Lưu session
        data = load_data()
        data["sessions"][session_token] = {
            "unique_key": unique_key,
            "created_at": time.time(),
            "verified": False,
            "owner_ip": user_ip,
            "ip_list": [user_ip],
            "max_ips": 3,
            "check_count": 0,
            "owner_user_agent": user_agent
        }
        save_data(data)
        
        print(f"[GET_LINK] Token: {session_token[:8]}... | Key: {unique_key[:8]}... | IP: {user_ip}")
        
        return jsonify({
            "status": "ok",
            "message": "Vui lòng vượt link để nhận key",
            "url": short_url,
            "token": session_token
        })
        
    except Exception as e:
        print(f"[ERROR] get_link: {e}")
        return jsonify({"status": "error", "msg": f"Lỗi: {str(e)}"})

@app.route("/k/<session_token>")
def get_key_page(session_token):
    """
    WEB HIỂN THỊ KEY - User vào sau khi vượt Link4m
    """
    current_ip = request.remote_addr
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
    
    # IP TRACKING
    ip_list = session.get("ip_list", [session.get("owner_ip")])
    max_ips = session.get("max_ips", 3)
    
    if current_ip not in ip_list:
        if len(ip_list) >= max_ips:
            return render_template_string(ERROR_PAGE, 
                error_msg=f"Key này đang được sử dụng trên {max_ips} thiết bị khác.")
        else:
            ip_list.append(current_ip)
            session["ip_list"] = ip_list
            print(f"[IP_ADD] Token: {session_token[:8]}... | Thêm IP: {current_ip} ({len(ip_list)}/{max_ips})")
    
    # SET VERIFIED
    session["verified"] = True
    data["sessions"][session_token] = session
    save_data(data)
    
    print(f"[KEY_PAGE] Token: {session_token[:8]}... | IP: {current_ip}")
    
    # Hiển thị key
    unique_key = session.get("unique_key")
    expire_time = created_at + 86400
    expire_str = time.strftime("%d/%m/%Y %H:%M:%S", time.localtime(expire_time))
    
    return render_template_string(SUCCESS_PAGE, 
        key=unique_key, 
        expire_at=expire_str,
        ips_used=len(ip_list),
        max_ips=max_ips)

@app.route("/api/get_key_by_token")
def get_key_by_token():
    """API cho TOOL - Lấy key bằng token (polling)"""
    session_token = request.args.get("token")
    
    if not session_token:
        return jsonify({"status": "error", "msg": "Thiếu token"})
    
    current_ip = request.remote_addr
    
    # Rate limiting
    ip_allowed, _ = check_rate_limit(f"ip:{current_ip}", max_requests=30, time_window=60)
    if not ip_allowed:
        return jsonify({"status": "error", "msg": "Quá nhiều requests."})
    
    data = load_data()
    
    if session_token not in data.get("sessions", {}):
        return jsonify({"status": "error", "msg": "Token không tồn tại"})
    
    session = data["sessions"][session_token]
    current_time = time.time()
    created_at = session.get("created_at", 0)
    
    # Kiểm tra hết hạn
    if current_time - created_at > 86400:
        del data["sessions"][session_token]
        save_data(data)
        return jsonify({"status": "error", "msg": "Token đã hết hạn"})
    
    # Kiểm tra verified
    if not session.get("verified"):
        return jsonify({
            "status": "waiting",
            "msg": "Vui lòng vượt link. Tool sẽ tự động nhận key."
        })
    
    # IP tracking
    ip_list = session.get("ip_list", [session.get("owner_ip")])
    max_ips = session.get("max_ips", 3)
    
    if current_ip not in ip_list:
        if len(ip_list) >= max_ips:
            return jsonify({
                "status": "error",
                "msg": f"Key đã được sử dụng trên {max_ips} thiết bị khác."
            })
        else:
            ip_list.append(current_ip)
            session["ip_list"] = ip_list
            data["sessions"][session_token] = session
            save_data(data)
    
    # Trả key
    unique_key = session.get("unique_key")
    expire_time = created_at + 86400
    expire_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expire_time))
    
    print(f"[GET_KEY_BY_TOKEN] Token: {session_token[:8]}... | Key: {unique_key[:8]}...")
    
    return jsonify({
        "status": "ok",
        "key": unique_key,
        "expire_at": expire_str,
        "msg": "Key đã sẵn sàng!"
    })

@app.route("/api/check_key")
def check_key():
    """API cho TOOL - Check key hợp lệ"""
    key = request.args.get("key")
    
    if not key:
        return jsonify({"status": "fail", "msg": "Thiếu key"})
    
    current_ip = request.remote_addr
    
    # Rate limiting
    ip_allowed, _ = check_rate_limit(f"ip:{current_ip}", max_requests=20, time_window=60)
    if not ip_allowed:
        return jsonify({"status": "fail", "msg": "Quá nhiều requests."})
    
    key_allowed, _ = check_rate_limit(f"key:{key}", max_requests=10, time_window=60)
    if not key_allowed:
        return jsonify({"status": "fail", "msg": "Key đang được check quá nhiều."})
    
    data = load_data()
    current_time = time.time()
    
    for session_token, session_data in data.get("sessions", {}).items():
        if session_data.get("unique_key") == key:
            created_at = session_data.get("created_at", 0)
            
            if current_time - created_at > 86400:
                del data["sessions"][session_token]
                save_data(data)
                return jsonify({"status": "fail", "msg": "Key đã hết hạn"})
            
            if not session_data.get("verified"):
                return jsonify({"status": "fail", "msg": "Key chưa được kích hoạt"})
            
            # IP tracking
            ip_list = session_data.get("ip_list", [session_data.get("owner_ip")])
            max_ips = session_data.get("max_ips", 3)
            
            if current_ip not in ip_list:
                if len(ip_list) >= max_ips:
                    return jsonify({"status": "fail", "msg": "Key đang được sử dụng trên thiết bị khác"})
                else:
                    ip_list.append(current_ip)
                    session_data["ip_list"] = ip_list
                    data["sessions"][session_token] = session_data
                    save_data(data)
            
            session_data["check_count"] = session_data.get("check_count", 0) + 1
            data["sessions"][session_token] = session_data
            save_data(data)
            
            expire_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(created_at + 86400))
            
            return jsonify({
                "status": "ok",
                "msg": "Key hợp lệ",
                "expire_at": expire_at,
                "ips_used": len(ip_list),
                "max_ips": max_ips
            })
    
    return jsonify({"status": "fail", "msg": "Key không tồn tại"})

# ==================== HTML TEMPLATES ====================

HOME_HTML = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ARES Tool - License System</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
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
        .container { max-width: 700px; text-align: center; }
        .logo {
            font-size: 72px;
            font-weight: bold;
            color: #00ff9d;
            text-shadow: 0 0 40px rgba(0, 255, 157, 0.6);
            letter-spacing: 10px;
            margin-bottom: 20px;
        }
        .subtitle { font-size: 24px; color: #ffc107; margin-bottom: 40px; }
        .info-box {
            background: rgba(255, 255, 255, 0.05);
            border: 2px solid #00ff9d;
            border-radius: 20px;
            padding: 40px;
            margin-bottom: 30px;
        }
        h2 { color: #00ff9d; margin-bottom: 20px; }
        p { font-size: 18px; line-height: 1.8; margin-bottom: 15px; color: rgba(255, 255, 255, 0.9); }
        .code {
            background: #1e293b;
            color: #00ff9d;
            padding: 15px;
            border-radius: 10px;
            font-family: 'Courier New', monospace;
            margin: 20px 0;
        }
        .warning {
            background: rgba(255, 193, 7, 0.1);
            border: 2px solid #ffc107;
            border-radius: 12px;
            padding: 20px;
            margin-top: 30px;
        }
        .warning h3 { color: #ffc107; margin-bottom: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">ARES</div>
        <div class="subtitle">LICENSE KEY SYSTEM V2.0</div>
        
        <div class="info-box">
            <h2>🎮 Hệ Thống License Cho Tool</h2>
            <p>Đây là hệ thống API cung cấp license key cho <strong>ARES Tool V23</strong>.</p>
            <p>Web này <strong>KHÔNG CÓ</strong> giao diện lấy key trực tiếp.</p>
        </div>
        
        <div class="info-box">
            <h2>📱 Cách Sử Dụng</h2>
            <p><strong>Bước 1:</strong> Tải và cài đặt ARES Tool trên Termux</p>
            <div class="code">git clone https://github.com/quocdung1303/arestool.git<br>cd arestool<br>pip install -r requirements.txt</div>
            <p><strong>Bước 2:</strong> Chạy tool</p>
            <div class="code">python obf-botcucvip.py</div>
            <p><strong>Bước 3:</strong> Tool sẽ tự động tạo link và hướng dẫn bạn lấy key</p>
        </div>
        
        <div class="warning">
            <h3>⚠️ Lưu Ý</h3>
            <p>• Key có hiệu lực 24 giờ</p>
            <p>• Hỗ trợ tối đa 3 IP (đổi mạng 4G/Wifi bình thường)</p>
            <p>• Hoàn toàn miễn phí</p>
        </div>
    </div>
</body>
</html>
"""

SUCCESS_PAGE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎉 Key Của Bạn - ARES Tool</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
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
        .container { max-width: 600px; width: 100%; }
        .success-box {
            background: rgba(255, 255, 255, 0.05);
            border: 2px solid #00ff9d;
            border-radius: 20px;
            padding: 40px;
            text-align: center;
            box-shadow: 0 0 40px rgba(0, 255, 157, 0.3);
        }
        .title { font-size: 48px; color: #00ff9d; margin-bottom: 10px; }
        .subtitle { font-size: 24px; color: #ffc107; margin-bottom: 30px; }
        .key-container {
            background: rgba(0, 0, 0, 0.3);
            border: 2px solid #00ff9d;
            border-radius: 15px;
            padding: 30px;
            margin: 30px 0;
        }
        .key-label { font-size: 18px; color: #00ff9d; margin-bottom: 15px; }
        .key-value {
            font-size: 20px;
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
        }
        .info {
            background: rgba(255, 193, 7, 0.1);
            border: 1px solid #ffc107;
            border-radius: 10px;
            padding: 20px;
            margin-top: 20px;
            text-align: left;
        }
        .info-item { margin: 10px 0; font-size: 16px; }
        .info-label { color: #ffc107; font-weight: bold; }
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
                <div class="key-label">🔑 LICENSE KEY:</div>
                <div class="key-value" id="keyValue">{{ key }}</div>
                <button class="copy-btn" onclick="copyKey()">📋 Copy Key</button>
            </div>
            
            <div class="info">
                <div class="info-item">
                    <span class="info-label">⏰ Hết hạn:</span> {{ expire_at }}
                </div>
                <div class="info-item">
                    <span class="info-label">💡 Lưu ý:</span> Key hoạt động tốt nhất trên 1 thiết bị
                </div>
                <div class="info-item">
                    <span class="info-label">✅ Hỗ trợ:</span> Đổi mạng 4G/Wifi bình thường
                </div>
            </div>
        </div>
    </div>
    
    <script>
        function copyKey() {
            const keyValue = document.getElementById('keyValue').innerText;
            navigator.clipboard.writeText(keyValue).then(() => {
                alert('✅ Đã copy key vào clipboard!');
            });
        }
    </script>
</body>
</html>
"""

ERROR_PAGE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>❌ Lỗi - ARES Tool</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
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
        .error-icon { font-size: 64px; margin-bottom: 20px; }
        .error-title { font-size: 28px; color: #ff4444; margin-bottom: 20px; }
        .error-msg { font-size: 18px; margin-bottom: 30px; line-height: 1.6; }
    </style>
</head>
<body>
    <div class="error-box">
        <div class="error-icon">❌</div>
        <div class="error-title">Có Lỗi Xảy Ra</div>
        <div class="error-msg">{{ error_msg }}</div>
    </div>
</body>
</html>
"""
