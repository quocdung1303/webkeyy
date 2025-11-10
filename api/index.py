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

# ✅ SỬA: Đổi sang endpoint /st có antibot mạnh hơn
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

# ✅ THÊM MỚI: Route tracking để đánh dấu đã vượt link
@app.route("/track")
def track():
    """Tracking khi user click vào link và hoàn thành antibot"""
    token = request.args.get("t")
    
    if not token:
        return """
        <script>window.location.href='/';</script>
        <p>Đang chuyển hướng...</p>
        """
    
    data = load_data()
    
    if token in data.get("sessions", {}):
        # Đánh dấu đã vượt link thành công
        data["sessions"][token]["link_clicked"] = True
        data["sessions"][token]["link_clicked_at"] = time.time()
        save_data(data)
    
    # Redirect về trang chủ với thông báo thành công
    return """
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Xác thực thành công - ARES</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                text-align: center;
                padding: 20px;
            }
            .card {
                background: rgba(255,255,255,0.1);
                backdrop-filter: blur(10px);
                padding: 50px 40px;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                max-width: 500px;
                width: 100%;
            }
            .icon { font-size: 80px; margin-bottom: 20px; animation: bounce 1s ease infinite; }
            @keyframes bounce {
                0%, 100% { transform: translateY(0); }
                50% { transform: translateY(-10px); }
            }
            h1 { font-size: 32px; margin-bottom: 15px; font-weight: 900; }
            p { font-size: 18px; opacity: 0.9; margin-bottom: 30px; line-height: 1.6; }
            .countdown { 
                font-size: 64px; 
                font-weight: 900; 
                color: #00ff9d;
                margin: 30px 0;
                text-shadow: 0 0 20px rgba(0,255,157,0.5);
            }
            .info {
                background: rgba(0,0,0,0.2);
                padding: 15px;
                border-radius: 10px;
                margin-bottom: 25px;
                font-size: 14px;
            }
            .btn {
                display: inline-block;
                padding: 15px 40px;
                background: white;
                color: #667eea;
                text-decoration: none;
                border-radius: 10px;
                font-weight: bold;
                font-size: 16px;
                transition: all 0.3s;
            }
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 25px rgba(255,255,255,0.3);
            }
        </style>
    </head>
    <body>
        <div class="card">
            <div class="icon">✅</div>
            <h1>Xác thực thành công!</h1>
            <p>Bạn đã vượt link thành công. Vui lòng đợi để nhận KEY.</p>
            
            <div class="info">
                ⏰ Thời gian còn lại
            </div>
            
            <div class="countdown" id="countdown">80</div>
            
            <a href="/" class="btn">Quay lại trang chủ</a>
        </div>
        <script>
            let seconds = 80;
            const countdownEl = document.getElementById('countdown');
            
            const timer = setInterval(() => {
                seconds--;
                if (seconds > 0) {
                    countdownEl.textContent = seconds;
                } else {
                    countdownEl.textContent = '✓';
                    countdownEl.style.color = '#00ff9d';
                    clearInterval(timer);
                }
            }, 1000);
        </script>
    </body>
    </html>
    """

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
    """Tạo link rút gọn Link4m với antibot"""
    if not LINK4M_KEY:
        return jsonify({"status": "error", "msg": "Chưa cấu hình LINK4M_KEY"})
    
    session_token = generate_session_token()
    unique_key = generate_key()
    
    # ✅ SỬA: URL đích trỏ đến endpoint tracking với session token
    destination_url = f"https://areskey.vercel.app/track?t={session_token}"
    
    try:
        # Sử dụng endpoint /st có antibot mạnh hơn
        create_url = f"{LINK4M_API}?api={LINK4M_KEY}&url={destination_url}"
        res = requests.get(create_url, timeout=10).json()
        
        if res.get("status") != "success" or not res.get("shortenedUrl"):
            return jsonify({"status": "error", "msg": "Không tạo được link rút gọn"})
        
        short_url = res["shortenedUrl"]
        
        # Lưu session
        data = load_data()
        data["sessions"][session_token] = {
            "unique_key": unique_key,
            "created_at": time.time(),
            "link_clicked": False,
            "link_clicked_at": 0,
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
    """Lấy KEY sau khi đã vượt link và đợi đủ thời gian"""
    session_token = request.args.get("token")
    
    if not session_token:
        return jsonify({"status": "error", "msg": "Thiếu token"})
    
    data = load_data()
    
    if session_token not in data.get("sessions", {}):
        return jsonify({"status": "error", "msg": "Session không tồn tại hoặc đã hết hạn"})
    
    session = data["sessions"][session_token]
    created_at = session.get("created_at", 0)
    current_time = time.time()
    
    # Kiểm tra hết hạn (quá 24 giờ)
    if current_time - created_at > 86400:
        del data["sessions"][session_token]
        save_data(data)
        return jsonify({"status": "error", "msg": "Session đã hết hạn (quá 24 giờ)"})
    
    # ✅ SỬA: Kiểm tra đã vượt link chưa
    if not session.get("link_clicked", False):
        return jsonify({"status": "error", "msg": "Vui lòng vượt link trước khi lấy KEY"})
    
    # ✅ SỬA: Kiểm tra thời gian đã đợi (tính từ lúc vượt link xong)
    link_clicked_at = session.get("link_clicked_at", created_at)
    time_since_click = current_time - link_clicked_at
    
    if time_since_click < 80:
        remaining = int(80 - time_since_click)
        return jsonify({"status": "error", "msg": f"Vui lòng đợi thêm {remaining} giây"})
    
    unique_key = session.get("unique_key")
    expire_time = created_at + 86400
    
    if not unique_key:
        return jsonify({"status": "error", "msg": "Key không tồn tại"})
    
    # Đánh dấu đã lấy key (giữ nguyên logic cũ)
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
            
            # Kiểm tra key đã hết hạn chưa
            if current_time - created_at > 86400:
                del data["sessions"][session_token]
                save_data(data)
                return jsonify({"status": "fail", "msg": "Key đã hết hạn (quá 24 giờ)"})
            
            # Kiểm tra giới hạn IP (tối đa 3 IP)
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
