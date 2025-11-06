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

#XOÁ DÒNG NÀY-KHÔNG CẦN NỮA
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

@app.route("/")
def home():
    """Trang chủ"""
    return render_template_string(INDEX_HTML)

@app.route("/api/get_link")
def get_link():
    """Tạo link rút gọn Link4m - API mới"""
    if not LINK4M_KEY:
        return jsonify({"status": "error", "msg": "Chưa cấu hình LINK4M_KEY"})
    
    session_token = generate_session_token()
    user_ip = request.remote_addr
    user_agent = request.headers.get('User-Agent', 'Unknown')
    
    # URL đích - ĐỔI DOMAIN NẾU CẦN
    destination_url = f"https://webkeyy.vercel.app/success?s={session_token}"
    
    try:
        # API MỚI của Link4m (format đơn giản hơn)
        api_url = f"https://link4m.co/api?api={LINK4M_KEY}&url={destination_url}"
        
        print(f"[INFO] Gọi Link4m API: {api_url}")
        
        response = requests.get(api_url, timeout=10)
        
        print(f"[INFO] Link4m response: {response.text}")
        
        # Link4m API trả về link rút gọn trực tiếp (text)
        short_url = response.text.strip()
        # Link4m API trả về link rút gọn trực tiếp (text)
short_url = response.text.strip()

# Lưu session
data = load_data()
data["sessions"][session_token] = {
    # ... code cũ ...
}
save_data(data)

print(f"[GET_LINK] Short URL: {short_url}")

return jsonify({
    "status": "ok",
    "message": "Vui lòng vượt link để nhận key",
    "url": short_url,
    "token": session_token
        })
        
        # Lưu session
        data = load_data()
        data["sessions"][session_token] = {
            "unique_key": None,
            "created_at": time.time(),
            "verified": False,
            "owner_ip": user_ip,
            "ip_list": [user_ip],
            "max_ips": 3,
            "check_count": 0,
            "owner_user_agent": user_agent
        }
        save_data(data)
        
        print(f"[GET_LINK] Token: {session_token[:8]}... | IP: {user_ip} | Short URL: {short_url}")
        
        return jsonify({
            "status": "ok",
            "message": "Vui lòng vượt link để nhận key",
            "url": short_url,
            "token": session_token
        })
        
    except Exception as e:
        print(f"[ERROR] get_link: {e}")
        return jsonify({"status": "error", "msg": f"Lỗi: {str(e)}"})

@app.route("/success")
def success_page():
    """Trang đích sau khi vượt Link4m - TỰ ĐỘNG TẠO VÀ HIỂN THỊ KEY"""
    session_token = request.args.get("id")
    
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
    
    # ===== THÊM: IP TRACKING (Max 3 IPs) =====
    ip_list = session.get("ip_list", [session.get("owner_ip")])
    max_ips = session.get("max_ips", 3)
    
    if current_ip not in ip_list:
        if len(ip_list) >= max_ips:
            return render_template_string(ERROR_PAGE, 
                error_msg=f"Key này đang được sử dụng trên {max_ips} thiết bị khác. Không được chia sẻ key! Vui lòng lấy key mới tại https://webkeyy.vercel.app")
        else:
            ip_list.append(current_ip)
            session["ip_list"] = ip_list
            print(f"[IP_ADD] Token: {session_token[:8]}... | Thêm IP: {current_ip} ({len(ip_list)}/{max_ips})")
    
    # TẠO KEY NẾU CHƯA CÓ (lần đầu vào trang success)
    if not session.get("unique_key"):
        session["unique_key"] = generate_key()
        session["verified"] = True
        print(f"[SUCCESS] Tạo key mới: {session['unique_key'][:8]}... | IP: {current_ip}")
    
    # Lưu session
    data["sessions"][session_token] = session
    save_data(data)
    
    unique_key = session["unique_key"]
    expire_time = created_at + 86400
    expire_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expire_time))
    
    return render_template_string(SUCCESS_PAGE, 
        key=unique_key, 
        expire_at=expire_str,
        ips_used=len(ip_list),
        max_ips=max_ips)

@app.route("/api/check_key")
def check_key():
    """Kiểm tra key có hợp lệ không - VỚI IP TRACKING & RATE LIMITING"""
    key = request.args.get("key")
    
    if not key:
        return jsonify({"status": "fail", "msg": "Thiếu key"})
    
    current_ip = request.remote_addr
    
    # ===== THÊM: RATE LIMITING - IP Level =====
    ip_allowed, ip_count = check_rate_limit(f"ip:{current_ip}", max_requests=20, time_window=60)
    if not ip_allowed:
        print(f"[RATE_LIMIT] IP {current_ip} vượt quá 20 req/phút")
        return jsonify({"status": "fail", "msg": "Quá nhiều requests từ IP của bạn. Vui lòng chờ 1 phút."})
    
    # ===== THÊM: RATE LIMITING - Key Level =====
    key_allowed, key_count = check_rate_limit(f"key:{key}", max_requests=10, time_window=60)
    if not key_allowed:
        print(f"[RATE_LIMIT] Key {key[:8]}... vượt quá 10 req/phút")
        return jsonify({"status": "fail", "msg": "Key đang được check quá nhiều lần. Vui lòng chờ."})
    
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
            
            # ===== THÊM: IP TRACKING (Max 3 IPs) =====
            ip_list = session_data.get("ip_list", [session_data.get("owner_ip")])
            max_ips = session_data.get("max_ips", 3)
            
            if current_ip not in ip_list:
                if len(ip_list) >= max_ips:
                    print(f"[IP_LIMIT] Key {key[:8]}... đã đủ {max_ips} IP | Current: {current_ip}")
                    return jsonify({
                        "status": "fail",
                        "msg": f"Key đang được sử dụng trên thiết bị khác. Vui lòng lấy key mới tại https://webkeyy.vercel.app"
                    })
                else:
                    ip_list.append(current_ip)
                    session_data["ip_list"] = ip_list
                    data["sessions"][session_token] = session_data
                    save_data(data)
                    print(f"[IP_ADD] Key {key[:8]}... thêm IP: {current_ip} ({len(ip_list)}/{max_ips})")
            
            # ===== THÊM: Update check count =====
            session_data["check_count"] = session_data.get("check_count", 0) + 1
            session_data["last_check"] = current_time
            data["sessions"][session_token] = session_data
            save_data(data)
            
            # Key hợp lệ
            expire_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(created_at + 86400))
            
            print(f"[OK] Key {key[:8]}... | IP: {current_ip} | Checks: {session_data['check_count']} | IPs: {len(ip_list)}/{max_ips}")
            
            return jsonify({
                "status": "ok",
                "msg": "Key hợp lệ",
                "expire_at": expire_at,
                "is_unique": True,
                "ips_used": len(ip_list),
                "max_ips": max_ips
            })
    
    return jsonify({"status": "fail", "msg": "Key không tồn tại hoặc không hợp lệ"})

@app.route("/huong-dan")
def huong_dan():
    """Trang hướng dẫn"""
    return render_template_string(HUONG_DAN_HTML)

# ==================== HTML TEMPLATES ====================

INDEX_HTML = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ARES Tool - Hệ Thống Quản Lý Key</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%);
            color: #fff;
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            padding-top: 40px;
        }
        .header {
            text-align: center;
            margin-bottom: 40px;
        }
        .logo {
            font-size: 64px;
            font-weight: bold;
            color: #00ff9d;
            text-shadow: 0 0 30px rgba(0, 255, 157, 0.5);
            letter-spacing: 8px;
            margin-bottom: 10px;
        }
        .subtitle {
            font-size: 18px;
            color: #ffc107;
            margin-bottom: 20px;
        }
        .description {
            font-size: 16px;
            color: rgba(255, 255, 255, 0.7);
            line-height: 1.6;
        }
        .status-bar {
            display: flex;
            gap: 10px;
            margin-bottom: 30px;
        }
        .status-item {
            flex: 1;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(0, 255, 157, 0.3);
            border-radius: 12px;
            padding: 15px;
            text-align: center;
        }
        .status-icon { font-size: 24px; margin-bottom: 8px; }
        .status-text { font-size: 14px; color: rgba(255, 255, 255, 0.8); }
        .main-card {
            background: rgba(255, 255, 255, 0.05);
            border: 2px solid #00ff9d;
            border-radius: 20px;
            padding: 40px;
            margin-bottom: 30px;
            box-shadow: 0 0 40px rgba(0, 255, 157, 0.2);
        }
        .card-title { font-size: 28px; color: #00ff9d; margin-bottom: 15px; text-align: center; }
        .card-description {
            font-size: 16px;
            color: rgba(255, 255, 255, 0.8);
            text-align: center;
            line-height: 1.6;
            margin-bottom: 30px;
        }
        .get-key-btn {
            width: 100%;
            background: linear-gradient(135deg, #00ff9d 0%, #00cc7d 100%);
            color: #0a0e27;
            border: none;
            padding: 18px;
            font-size: 20px;
            font-weight: bold;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .get-key-btn:hover { transform: translateY(-2px); box-shadow: 0 10px 30px rgba(0, 255, 157, 0.4); }
        .get-key-btn:disabled { background: rgba(255, 255, 255, 0.2); cursor: not-allowed; transform: none; }
        .link-box {
            background: rgba(255, 193, 7, 0.1);
            border: 2px solid #ffc107;
            border-radius: 15px;
            padding: 25px;
            margin-top: 20px;
            display: none;
        }
        .link-box.active { display: block; animation: fadeIn 0.3s ease-in; }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .link-title { font-size: 20px; color: #ffc107; margin-bottom: 15px; text-align: center; }
        .link-instruction {
            font-size: 15px;
            color: rgba(255, 255, 255, 0.9);
            margin-bottom: 20px;
            text-align: center;
            line-height: 1.5;
        }
        .link-button {
            width: 100%;
            background: #ffc107;
            color: #0a0e27;
            border: none;
            padding: 16px;
            font-size: 18px;
            font-weight: bold;
            border-radius: 10px;
            cursor: pointer;
            text-decoration: none;
            display: block;
            text-align: center;
        }
        .link-button:hover { background: #ffb300; transform: scale(1.02); }
        .info-box {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            padding: 25px;
        }
        .info-item { display: flex; align-items: flex-start; margin-bottom: 15px; }
        .info-item:last-child { margin-bottom: 0; }
        .info-icon { font-size: 20px; margin-right: 12px; flex-shrink: 0; }
        .info-text { font-size: 15px; color: rgba(255, 255, 255, 0.8); line-height: 1.5; }
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid rgba(255, 255, 255, 0.3);
            border-top-color: #0a0e27;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .error-msg {
            background: rgba(255, 68, 68, 0.1);
            border: 1px solid #ff4444;
            border-radius: 10px;
            padding: 15px;
            margin-top: 15px;
            color: #ff4444;
            text-align: center;
            display: none;
        }
        .error-msg.active { display: block; }
        .link { color: #00ff9d; text-decoration: none; font-weight: 600; }
        .link:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">ARES</div>
            <div class="subtitle">LICENSE KEY SYSTEM V2.0 - IP TRACKING</div>
            <div class="description">
                Nhận key miễn phí với hiệu lực 24 giờ để sử dụng ARES Tool
            </div>
        </div>

        <div class="status-bar">
            <div class="status-item">
                <div class="status-icon">✅</div>
                <div class="status-text">Hệ thống hoạt động</div>
            </div>
            <div class="status-item">
                <div class="status-icon">🔑</div>
                <div class="status-text">Key 24 giờ</div>
            </div>
            <div class="status-item">
                <div class="status-icon">🔒</div>
                <div class="status-text">Bảo mật cao</div>
            </div>
        </div>

        <div class="main-card">
            <div class="card-title">🎁 Nhận Key Miễn Phí</div>
            <div class="card-description">
                Click vào nút bên dưới để nhận link. Sau khi vượt link quảng cáo, 
                bạn sẽ tự động nhận được key riêng có hiệu lực 24 giờ.
            </div>

            <button class="get-key-btn" id="getKeyBtn" onclick="getLink()">
                <span id="btnText">🔑 Lấy Key Ngay</span>
            </button>

            <div class="error-msg" id="errorMsg"></div>

            <div class="link-box" id="linkBox">
                <div class="link-title">🔗 Link Của Bạn</div>
                <div class="link-instruction">
                    Click vào nút bên dưới để vượt link quảng cáo Link4m. 
                    <strong>Sau khi vượt xong, bạn sẽ tự động nhận được key!</strong>
                </div>
                <a class="link-button" id="link4mButton" href="#" target="_blank">
                    ↗ Vượt Link Để Nhận Key
                </a>
            </div>
        </div>

        <div class="info-box">
            <div class="info-item">
                <div class="info-icon">⏰</div>
                <div class="info-text">
                    Key riêng cho từng người • Hiệu lực 24 giờ
                </div>
            </div>
            <div class="info-item">
                <div class="info-icon">🔒</div>
                <div class="info-text">
                    Key hoạt động tốt nhất khi dùng trên 1 thiết bị. Hỗ trợ đổi mạng 4G/Wifi bình thường.
                </div>
            </div>
            <div class="info-item">
                <div class="info-icon">📖</div>
                <div class="info-text">
                    <a href="/huong-dan" class="link">Xem hướng dẫn cài đặt tool →</a>
                </div>
            </div>
        </div>
    </div>

    <script>
        async function getLink() {
            const btn = document.getElementById('getKeyBtn');
            const btnText = document.getElementById('btnText');
            const linkBox = document.getElementById('linkBox');
            const link4mButton = document.getElementById('link4mButton');
            const errorMsg = document.getElementById('errorMsg');

            errorMsg.classList.remove('active');
            btn.disabled = true;
            btnText.innerHTML = '<span class="loading"></span> Đang tạo link...';

            try {
                const response = await fetch('/api/get_link');
                const data = await response.json();

                if (data.status === 'ok') {
                    linkBox.classList.add('active');
                    link4mButton.href = data.url;
                    btnText.textContent = '✅ Đã tạo link thành công';
                    linkBox.scrollIntoView({ behavior: 'smooth', block: 'center' });
                } else {
                    throw new Error(data.msg || 'Không thể tạo link');
                }
            } catch (error) {
                errorMsg.textContent = '❌ Lỗi: ' + error.message;
                errorMsg.classList.add('active');
                btnText.textContent = '🔑 Lấy Key Ngay';
                btn.disabled = false;
            }
        }
    </script>
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
            animation: fadeIn 0.5s ease-in;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .title { font-size: 48px; color: #00ff9d; margin-bottom: 10px; text-shadow: 0 0 20px rgba(0, 255, 157, 0.5); }
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
        .copy-btn:hover { background: #00cc7d; transform: scale(1.05); }
        .copy-btn:active { transform: scale(0.95); }
        .info {
            background: rgba(255, 193, 7, 0.1);
            border: 1px solid #ffc107;
            border-radius: 10px;
            padding: 20px;
            margin-top: 20px;
        }
        .info-item { margin: 10px 0; font-size: 16px; }
        .info-label { color: #ffc107; font-weight: bold; }
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
        .back-btn:hover { background: rgba(0, 255, 157, 0.2); }
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
                    <span class="info-label">💡 Lưu ý:</span> Key hoạt động tốt nhất khi dùng trên 1 thiết bị
                </div>
                <div class="info-item">
                    <span class="info-label">✅ Hỗ trợ:</span> Đổi mạng 4G/Wifi bình thường
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
        .back-btn:hover { background: #00cc7d; transform: scale(1.05); }
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

HUONG_DAN_HTML = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hướng Dẫn Cài Đặt - ARES Tool V23</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
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
            background: rgba(255, 255, 255, 0.05);
            border: 2px solid rgba(0, 255, 157, 0.3);
            border-radius: 20px;
            padding: 40px;
        }
        h1 {
            color: #00ff9d;
            text-align: center;
            font-size: 36px;
            margin-bottom: 10px;
            text-shadow: 0 0 20px rgba(0, 255, 157, 0.5);
        }
        .subtitle {
            text-align: center;
            color: #ffc107;
            margin-bottom: 40px;
            font-size: 18px;
        }
        .section {
            margin-bottom: 40px;
        }
        .section h2 {
            color: #00ff9d;
            margin-bottom: 15px;
            font-size: 24px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .step-number {
            background: #00ff9d;
            color: #0a0e27;
            width: 35px;
            height: 35px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 18px;
        }
        .code-block {
            background: #1e293b;
            border: 2px solid #00ff9d;
            border-radius: 12px;
            padding: 20px;
            margin: 15px 0;
            position: relative;
            overflow-x: auto;
        }
        .code-block code {
            color: #00ff9d;
            font-family: 'Courier New', monospace;
            font-size: 15px;
            display: block;
            white-space: pre-wrap;
        }
        .copy-btn {
            position: absolute;
            top: 10px;
            right: 10px;
            background: #ffc107;
            color: #0a0e27;
            border: none;
            padding: 8px 15px;
            border-radius: 6px;
            cursor: pointer;
            font-weight: bold;
            font-size: 12px;
            transition: all 0.3s;
        }
        .copy-btn:hover {
            background: #ffb300;
            transform: scale(1.05);
        }
        .info-box {
            background: rgba(0, 255, 157, 0.1);
            border: 2px solid #00ff9d;
            border-radius: 12px;
            padding: 20px;
            margin: 20px 0;
        }
        .info-box h3 {
            color: #00ff9d;
            margin-bottom: 10px;
        }
        .warning-box {
            background: rgba(255, 193, 7, 0.1);
            border: 2px solid #ffc107;
            border-radius: 12px;
            padding: 20px;
            margin: 20px 0;
        }
        .warning-box h3 {
            color: #ffc107;
            margin-bottom: 10px;
        }
        .info-item {
            display: flex;
            align-items: flex-start;
            gap: 10px;
            margin-bottom: 10px;
            line-height: 1.6;
        }
        .back-btn {
            display: inline-block;
            background: linear-gradient(135deg, #00ff9d 0%, #00cc7d 100%);
            color: #0a0e27;
            padding: 15px 40px;
            border-radius: 12px;
            text-decoration: none;
            font-weight: bold;
            font-size: 16px;
            transition: all 0.3s;
            box-shadow: 0 0 20px rgba(0, 255, 157, 0.3);
            margin-top: 30px;
        }
        .back-btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 30px rgba(0, 255, 157, 0.5);
        }
        .link {
            color: #00ff9d;
            text-decoration: none;
            font-weight: 600;
        }
        .link:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎮 ARES TOOL V23</h1>
        <div class="subtitle">Hướng Dẫn Cài Đặt & Sử Dụng</div>

        <!-- BƯỚC 1 -->
        <div class="section">
            <h2><span class="step-number">1</span> Tải & Cài Đặt Termux</h2>
            <p>⚠️ <strong>QUAN TRỌNG:</strong> Không tải Termux từ Google Play Store!</p>
            <div class="warning-box">
                <h3>📥 Tải Termux từ F-Droid:</h3>
                <div class="info-item">
                    🔗 <a href="https://f-droid.org/en/packages/com.termux/" class="link" target="_blank">
                        https://f-droid.org/en/packages/com.termux/
                    </a>
                </div>
                <div class="info-item">
                    💡 Phiên bản Play Store không còn được cập nhật và có thể gây lỗi
                </div>
            </div>
        </div>

        <!-- BƯỚC 2 -->
        <div class="section">
            <h2><span class="step-number">2</span> Cài Đặt Môi Trường</h2>
            <p>Mở Termux và chạy từng lệnh sau:</p>
            
            <div class="code-block">
                <button class="copy-btn" onclick="copyCode(this, 'pkg update && pkg upgrade -y')">📋 Copy</button>
                <code>pkg update && pkg upgrade -y</code>
            </div>
            <div class="info-item">⏱️ Chờ 2-5 phút để cập nhật</div>
            
            <div class="code-block">
                <button class="copy-btn" onclick="copyCode(this, 'pkg install python git -y')">📋 Copy</button>
                <code>pkg install python git -y</code>
            </div>
            <div class="info-item">📦 Cài đặt Python và Git</div>
        </div>

        <!-- BƯỚC 3 -->
        <div class="section">
            <h2><span class="step-number">3</span> Tải Tool Từ GitHub</h2>
            
            <div class="code-block">
                <button class="copy-btn" onclick="copyCode(this, 'git clone https://github.com/quocdung1303/arestool.git')">📋 Copy</button>
                <code>git clone https://github.com/quocdung1303/arestool.git</code>
            </div>
            
            <div class="code-block">
                <button class="copy-btn" onclick="copyCode(this, 'cd arestool')">📋 Copy</button>
                <code>cd arestool</code>
            </div>
            
            <div class="code-block">
                <button class="copy-btn" onclick="copyCode(this, 'pip install -r requirements.txt')">📋 Copy</button>
                <code>pip install -r requirements.txt</code>
            </div>
            <div class="info-item">⏱️ Chờ cài đặt thư viện (requests, colorama, websocket-client)</div>
        </div>

        <!-- BƯỚC 4 -->
        <div class="section">
            <h2><span class="step-number">4</span> Lấy License Key</h2>
            
            <div class="info-box">
                <h3>🔑 Cách Lấy Key:</h3>
                <div class="info-item">1️⃣ Vào trang chủ: <a href="/" class="link">webkeyy.vercel.app</a></div>
                <div class="info-item">2️⃣ Click nút "Lấy Key Ngay"</div>
                <div class="info-item">3️⃣ Hoàn thành bước xác minh Link4m</div>
                <div class="info-item">4️⃣ Copy key hiển thị trên màn hình</div>
                <div class="info-item">⏰ Key có hiệu lực 24 giờ</div>
            </div>
        </div>

        <!-- BƯỚC 5 -->
        <div class="section">
            <h2><span class="step-number">5</span> Chạy Tool</h2>
            
            <div class="code-block">
                <button class="copy-btn" onclick="copyCode(this, 'python obf-botcucvip.py')">📋 Copy</button>
                <code>python obf-botcucvip.py</code>
            </div>
            
            <div class="info-item">📝 Nhập license key khi được yêu cầu</div>
            <div class="info-item">✅ Tool sẽ tự động kết nối và bắt đầu chạy</div>
        </div>

        <!-- LƯU Ý SỬ DỤNG -->
        <div class="section">
            <h2>💡 Lưu Ý Khi Sử Dụng</h2>
            <div class="info-box">
                <div class="info-item">✅ Mỗi key có hiệu lực 24 giờ kể từ khi lấy</div>
                <div class="info-item">✅ Key hoạt động tốt nhất khi dùng trên 1 thiết bị</div>
                <div class="info-item">✅ Hỗ trợ đổi mạng 4G/Wifi trong quá trình sử dụng</div>
                <div class="info-item">✅ Sau 24h, quay lại trang chủ để lấy key mới</div>
                <div class="info-item">✅ Hoàn toàn miễn phí, không giới hạn số lần lấy key</div>
            </div>
        </div>

        <!-- XỬ LÝ LỖI -->
        <div class="section">
            <h2>🔧 Xử Lý Lỗi Thường Gặp</h2>
            
            <div class="warning-box">
                <h3>Lỗi: "Key không hợp lệ"</h3>
                <div class="info-item">• Kiểm tra key còn hạn không (24h kể từ khi lấy)</div>
                <div class="info-item">• Đảm bảo copy đúng key (không thừa khoảng trắng)</div>
                <div class="info-item">• Thử lấy key mới tại trang chủ</div>
            </div>

            <div class="warning-box">
                <h3>Lỗi: "Key đang được sử dụng"</h3>
                <div class="info-item">• Đóng tool trên thiết bị khác nếu đang chạy</div>
                <div class="info-item">• Chờ vài phút rồi thử lại</div>
                <div class="info-item">• Nếu vẫn lỗi, lấy key mới sau 24h</div>
            </div>

            <div class="warning-box">
                <h3>Lỗi: "Quá nhiều requests"</h3>
                <div class="info-item">• Chờ 1-2 phút rồi thử lại</div>
                <div class="info-item">• Tránh khởi động lại tool liên tục</div>
            </div>

            <div class="warning-box">
                <h3>Tool không kết nối được</h3>
                <div class="info-item">• Kiểm tra kết nối mạng</div>
                <div class="info-item">• Khởi động lại Termux</div>
                <div class="info-item">• Cập nhật tool: <code style="color: #ffc107;">cd arestool && git pull</code></div>
            </div>
        </div>

        <!-- MẸO -->
        <div class="section">
            <h2>✨ Mẹo Sử Dụng Hiệu Quả</h2>
            <div class="info-box">
                <div class="info-item">💡 Dùng wifi ổn định để tool chạy mượt mà hơn</div>
                <div class="info-item">💡 Lấy key vào đầu ngày để có thời gian sử dụng tối đa</div>
                <div class="info-item">💡 Không tắt Termux khi tool đang chạy</div>
                <div class="info-item">💡 Bookmark trang chủ để lấy key nhanh hơn</div>
            </div>
        </div>

        <!-- LIÊN HỆ -->
        <div class="section">
            <h2>📞 Hỗ Trợ</h2>
            <div class="info-item">💬 Nếu cần hỗ trợ, liên hệ admin qua Telegram/Discord</div>
            <div class="info-item">📖 GitHub: <a href="https://github.com/quocdung1303/arestool" class="link" target="_blank">github.com/quocdung1303/arestool</a></div>
            <div class="info-item">🌟 Nhớ star repo nếu thấy tool hữu ích!</div>
        </div>

        <center>
            <a href="/" class="back-btn">← Về Trang Chủ Lấy Key</a>
        </center>
    </div>

    <script>
        function copyCode(btn, text) {
            navigator.clipboard.writeText(text).then(() => {
                const originalText = btn.textContent;
                btn.textContent = '✅ Đã copy!';
                btn.style.background = '#00ff9d';
                
                setTimeout(() => {
                    btn.textContent = originalText;
                    btn.style.background = '#ffc107';
                }, 2000);
            }).catch(() => {
                alert('Vui lòng copy thủ công: ' + text);
            });
        }
    </script>
</body>
</html>
"""
