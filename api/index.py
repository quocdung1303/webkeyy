from flask import Flask, request, jsonify
import json
import os
import time
import random
import string
import secrets
import requests
import hashlib

app = Flask(__name__)

LINK4M_API = "https://link4m.co/st"
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
        print(f"[CLEANUP] Đã xóa {len(sessions_to_delete)} session hết hạn")

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

@app.route("/huong-dan")
def huong_dan():
    """Trang hướng dẫn"""
    try:
        with open('folder/huongdan.html', 'r', encoding='utf-8') as f:
            return f.read()
    except:
        return "huongdan.html not found"

@app.route("/dashboard")
def dashboard():
    """Trang dashboard thống kê - Yêu cầu mật khẩu"""
    password = request.args.get("password")
    correct_password = os.getenv("DASHBOARD_PASSWORD", "arestool2025")
    
    if password != correct_password:
        return """
        <!DOCTYPE html>
        <html lang="vi">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>ARES - Dashboard Login</title>
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body {
                    font-family: 'Segoe UI', system-ui, sans-serif;
                    background: #0a0e1a;
                    color: #fff;
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 20px;
                }
                .login-card {
                    background: linear-gradient(135deg, rgba(0, 255, 157, 0.05) 0%, rgba(0, 180, 140, 0.05) 100%);
                    border: 2px solid rgba(0, 255, 157, 0.2);
                    border-radius: 16px;
                    padding: 40px;
                    max-width: 400px;
                    width: 100%;
                    text-align: center;
                }
                .logo {
                    font-size: 56px;
                    font-weight: 900;
                    color: #00ff9d;
                    text-shadow: 0 0 20px rgba(0, 255, 157, 0.5);
                    font-family: 'Courier New', monospace;
                    margin-bottom: 10px;
                }
                .subtitle {
                    color: #ffc107;
                    font-size: 14px;
                    font-weight: 600;
                    margin-bottom: 30px;
                    letter-spacing: 2px;
                }
                .lock-icon {
                    font-size: 48px;
                    margin-bottom: 20px;
                }
                .input-group {
                    margin-bottom: 20px;
                }
                .input-group input {
                    width: 100%;
                    padding: 15px;
                    background: rgba(0, 0, 0, 0.3);
                    border: 1px solid rgba(0, 255, 157, 0.3);
                    border-radius: 8px;
                    color: #fff;
                    font-size: 16px;
                }
                .input-group input:focus {
                    outline: none;
                    border-color: #00ff9d;
                }
                .btn {
                    width: 100%;
                    padding: 15px;
                    background: #00ff9d;
                    color: #0a0e1a;
                    border: none;
                    border-radius: 8px;
                    font-size: 16px;
                    font-weight: 700;
                    cursor: pointer;
                    transition: all 0.3s;
                }
                .btn:hover {
                    background: #00ffaa;
                    transform: translateY(-2px);
                }
                .error {
                    color: #ff4d4d;
                    font-size: 14px;
                    margin-top: 15px;
                    display: none;
                }
            </style>
        </head>
        <body>
            <div class="login-card">
                <div class="lock-icon">🔒</div>
                <div class="logo">ARES</div>
                <div class="subtitle">DASHBOARD - ĐĂNG NHẬP</div>
                <form onsubmit="login(event)">
                    <div class="input-group">
                        <input type="password" id="password" placeholder="Nhập mật khẩu" required autofocus>
                    </div>
                    <button type="submit" class="btn">Đăng nhập</button>
                    <div class="error" id="error">❌ Mật khẩu không đúng!</div>
                </form>
            </div>
            <script>
                function login(e) {
                    e.preventDefault();
                    const password = document.getElementById('password').value;
                    window.location.href = '/dashboard?password=' + encodeURIComponent(password);
                }
                
                const urlParams = new URLSearchParams(window.location.search);
                if (urlParams.has('password')) {
                    document.getElementById('error').style.display = 'block';
                }
            </script>
        </body>
        </html>
        """, 401
    
    try:
        with open('folder/dashboard.html', 'r', encoding='utf-8') as f:
            return f.read()
    except:
        return "dashboard.html not found"

@app.route("/api/stats")
def get_stats():
    """API lấy thống kê - Yêu cầu mật khẩu"""
    password = request.args.get("password")
    correct_password = os.getenv("DASHBOARD_PASSWORD", "arestool2025")
    
    if password != correct_password:
        return jsonify({"status": "error", "msg": "Unauthorized"}), 401
    
    data = load_data()
    sessions = data.get("sessions", {})
    current_time = time.time()
    
    total_sessions = len(sessions)
    completed = 0
    pending = 0
    active = 0
    
    sessions_list = []
    
    for session_token, session_data in sessions.items():
        created_at = session_data.get("created_at", 0)
        is_expired = (current_time - created_at) > 86400
        is_completed = session_data.get("link_clicked", False)
        
        if not is_expired:
            active += 1
            if is_completed:
                completed += 1
            else:
                pending += 1
        
        status = "expired" if is_expired else ("completed" if is_completed else "pending")
        
        sessions_list.append({
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(created_at)),
            "expire_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(created_at + 86400)),
            "key": session_data.get("unique_key", "N/A"),
            "status": status,
            "ip_count": len(session_data.get("ip_list", []))
        })
    
    sessions_list.sort(key=lambda x: x["created_at"], reverse=True)
    
    return jsonify({
        "status": "ok",
        "total_sessions": total_sessions,
        "completed": completed,
        "pending": pending,
        "active": active,
        "sessions": sessions_list[:50]
    })

@app.route("/api/get_link")
def get_link():
    """Tạo link rút gọn Link4m"""
    if not LINK4M_KEY:
        return jsonify({"status": "error", "msg": "Chưa cấu hình LINK4M_KEY"})
    
    session_token = generate_session_token()
    unique_key = generate_key()
    
    short_hash = hashlib.md5(session_token.encode()).hexdigest()[:8]
    destination_url = f"https://areskey.vercel.app?s={short_hash}"
    
    try:
        create_url = f"{LINK4M_API}?api={LINK4M_KEY}&url={destination_url}"
        res = requests.get(create_url, timeout=10).json()
        
        if res.get("status") != "success" or not res.get("shortenedUrl"):
            return jsonify({"status": "error", "msg": "Không tạo được link rút gọn"})
        
        short_url = res["shortenedUrl"]
        
        data = load_data()
        data["sessions"][session_token] = {
            "unique_key": unique_key,
            "created_at": time.time(),
            "link_clicked": False,
            "ip_list": []
        }
        save_data(data)
        
        return jsonify({
            "status": "ok",
            "message": "Vui lòng vượt link",
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
    
    if current_time - created_at > 86400:
        del data["sessions"][session_token]
        save_data(data)
        return jsonify({"status": "error", "msg": "Session đã hết hạn (quá 24 giờ)"})
    
    time_elapsed = current_time - created_at
    if time_elapsed < 80:
        return jsonify({"status": "error", "msg": "Vui lòng vượt link"})
    
    unique_key = session.get("unique_key")
    expire_time = created_at + 86400
    
    if not unique_key:
        return jsonify({"status": "error", "msg": "Key không tồn tại"})
    
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
    current_ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
    
    for session_token, session_data in data.get("sessions", {}).items():
        if session_data.get("unique_key") == key:
            created_at = session_data.get("created_at", 0)
            
            if current_time - created_at > 86400:
                del data["sessions"][session_token]
                save_data(data)
                return jsonify({"status": "fail", "msg": "Key đã hết hạn (quá 24 giờ)"})
            
            ip_list = session_data.get("ip_list", [])
            max_ips = 3
            
            if current_ip not in ip_list:
                if len(ip_list) >= max_ips:
                    return jsonify({"status": "fail", "msg": f"Key đã đạt giới hạn {max_ips} IP. Vui lòng lấy key mới."})
                
                ip_list.append(current_ip)
                data["sessions"][session_token]["ip_list"] = ip_list
                save_data(data)
            
            expire_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(created_at + 86400))
            return jsonify({
                "status": "ok",
                "msg": "Key hợp lệ",
                "date": expire_at,
                "expire_at": expire_at,
                "is_unique": True
            })
    
    return jsonify({"status": "fail", "msg": "Key không tồn tại hoặc không hợp lệ"})
