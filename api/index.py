from flask import Flask, request, jsonify, render_template_string
import time
import secrets
import json
import os
from collections import defaultdict, deque

app = Flask(__name__)

# ==================== CẤU HÌNH ====================
SESSIONS_FILE = "/tmp/sessions.json"
LINK4M_KEY = os.environ.get("LINK4M_KEY", "your_link4m_key_here")

# Rate limiting storage (in-memory)
rate_limit_storage = defaultdict(lambda: deque(maxlen=100))

# ==================== SESSIONS MANAGEMENT ====================

def load_sessions():
    """Load sessions từ file và tự động cleanup keys hết hạn"""
    if os.path.exists(SESSIONS_FILE):
        try:
            with open(SESSIONS_FILE, "r") as f:
                data = json.load(f)
                current_time = time.time()
                
                # Cleanup keys đã hết hạn
                valid_sessions = {}
                expired_count = 0
                
                for key, session in data.items():
                    if session.get("expire_at", 0) > current_time:
                        valid_sessions[key] = session
                    else:
                        expired_count += 1
                
                if expired_count > 0:
                    print(f"[CLEANUP] Đã xóa {expired_count} keys hết hạn")
                    save_sessions(valid_sessions)
                
                return valid_sessions
        except Exception as e:
            print(f"[ERROR] Lỗi load sessions: {e}")
            return {}
    return {}

def save_sessions(sessions_dict):
    """Lưu sessions vào file"""
    try:
        with open(SESSIONS_FILE, "w") as f:
            json.dump(sessions_dict, f, indent=2)
        return True
    except Exception as e:
        print(f"[ERROR] Lỗi save sessions: {e}")
        return False

# ==================== RATE LIMITING ====================

def check_rate_limit(identifier, max_requests=10, time_window=60):
    """
    Check rate limit cho một identifier (key hoặc IP)
    max_requests: Số requests tối đa
    time_window: Trong khoảng thời gian (giây)
    """
    current_time = time.time()
    request_times = rate_limit_storage[identifier]
    
    # Xóa requests cũ hơn time_window
    while request_times and current_time - request_times[0] > time_window:
        request_times.popleft()
    
    # Check có vượt quá limit không
    if len(request_times) >= max_requests:
        return False, len(request_times)
    
    # Thêm request mới
    request_times.append(current_time)
    return True, len(request_times)

# ==================== HELPER FUNCTIONS ====================

def generate_unique_key():
    """Tạo key ngẫu nhiên 24 ký tự"""
    return secrets.token_urlsafe(18)

def get_client_ip():
    """Lấy IP thật của client (xử lý proxy)"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr

# ==================== ROUTES ====================

@app.route("/")
def index():
    """Trang chủ lấy key"""
    return render_template_string(INDEX_HTML)

@app.route("/api/get_link")
@app.route("/api/get_link")
def get_link():
    """Tạo link rút gọn Link4m"""
    try:
        import requests
        
        # Gọi API Link4m
        api_url = f"https://link4m.co/api?api={LINK4M_KEY}&url=https://webkeyy.vercel.app/success"
        
        print(f"[INFO] Đang gọi Link4m API...")
        response = requests.get(api_url, timeout=10)
        
        if response.status_code == 200:
            shortened_link = response.text.strip()
            
            # Kiểm tra link hợp lệ
            if shortened_link.startswith('http'):
                print(f"[SUCCESS] Link rút gọn: {shortened_link}")
                return jsonify({
                    "status": "ok",
                    "link": shortened_link
                })
            else:
                print(f"[ERROR] Link4m trả về: {shortened_link}")
                return jsonify({
                    "status": "error",
                    "msg": "Link4m API lỗi: " + shortened_link
                }), 500
        else:
            print(f"[ERROR] HTTP {response.status_code}")
            return jsonify({
                "status": "error",
                "msg": f"Link4m API lỗi (HTTP {response.status_code})"
            }), 500
            
    except requests.Timeout:
        print("[ERROR] Timeout khi gọi Link4m")
        return jsonify({
            "status": "error",
            "msg": "Link4m không phản hồi. Vui lòng thử lại."
        }), 500
    except Exception as e:
        print(f"[ERROR] get_link: {e}")
        return jsonify({
            "status": "error",
            "msg": "Không thể tạo link. Vui lòng thử lại sau."
        }), 500

@app.route("/success")
def success():
    """Trang hiển thị key sau khi vượt link"""
    user_ip = get_client_ip()
    current_time = time.time()
    expire_time = current_time + (24 * 3600)  # 24 giờ
    
    # Tạo key mới
    unique_key = generate_unique_key()
    
    # Load sessions
    sessions = load_sessions()
    
    # Lưu session mới
    sessions[unique_key] = {
        "created_at": current_time,
        "expire_at": expire_time,
        "ip_list": [user_ip],  # List IP (cho phép đổi IP)
        "max_ips": 3,          # Tối đa 3 IP
        "type": "free",        # free hoặc vip
        "check_count": 0       # Số lần check
    }
    
    # Save sessions
    save_sessions(sessions)
    
    expire_str = time.strftime("%d/%m/%Y %H:%M:%S", time.localtime(expire_time))
    
    print(f"[SUCCESS] Key mới: {unique_key[:8]}... | IP: {user_ip}")
    
    return render_template_string(SUCCESS_HTML, 
                                   key=unique_key, 
                                   expire_time=expire_str)

@app.route("/api/check_key")
def check_key():
    """API check key - Có rate limiting và IP tracking"""
    
    key = request.args.get("key", "").strip()
    user_ip = get_client_ip()
    current_time = time.time()
    
    # ===== VALIDATION =====
    if not key:
        return jsonify({
            "status": "error",
            "msg": "Thiếu key"
        }), 400
    
    # ===== RATE LIMITING - IP Level =====
    ip_allowed, ip_count = check_rate_limit(f"ip:{user_ip}", max_requests=20, time_window=60)
    if not ip_allowed:
        print(f"[RATE_LIMIT] IP {user_ip} vượt quá 20 req/phút")
        return jsonify({
            "status": "error",
            "msg": "Quá nhiều requests từ IP của bạn. Vui lòng chờ 1 phút."
        }), 429
    
    # ===== RATE LIMITING - Key Level =====
    key_allowed, key_count = check_rate_limit(f"key:{key}", max_requests=10, time_window=60)
    if not key_allowed:
        print(f"[RATE_LIMIT] Key {key[:8]}... vượt quá 10 req/phút")
        return jsonify({
            "status": "error",
            "msg": "Key đang được check quá nhiều lần. Vui lòng chờ."
        }), 429
    
    # ===== LOAD SESSIONS =====
    sessions = load_sessions()
    
    if key not in sessions:
        print(f"[CHECK] Key {key[:8]}... không tồn tại | IP: {user_ip}")
        return jsonify({
            "status": "error",
            "msg": "Key không tồn tại hoặc đã hết hạn"
        }), 404
    
    session = sessions[key]
    
    # ===== CHECK EXPIRE =====
    if current_time > session.get("expire_at", 0):
        print(f"[EXPIRE] Key {key[:8]}... đã hết hạn | IP: {user_ip}")
        del sessions[key]
        save_sessions(sessions)
        return jsonify({
            "status": "error",
            "msg": "Key đã hết hạn (quá 24 giờ)"
        }), 403
    
    # ===== IP TRACKING (Max 3 IPs) =====
    ip_list = session.get("ip_list", [])
    max_ips = session.get("max_ips", 3)
    
    if user_ip not in ip_list:
        # IP mới chưa có trong list
        if len(ip_list) >= max_ips:
            # Đã đủ số IP
            print(f"[IP_LIMIT] Key {key[:8]}... đã đủ {max_ips} IP | Current: {user_ip}")
            return jsonify({
                "status": "error",
                "msg": f"Key đang được sử dụng trên {max_ips} thiết bị khác. Không được chia sẻ key!"
            }), 403
        else:
            # Thêm IP mới
            ip_list.append(user_ip)
            session["ip_list"] = ip_list
            sessions[key] = session
            save_sessions(sessions)
            print(f"[IP_ADD] Key {key[:8]}... thêm IP: {user_ip} ({len(ip_list)}/{max_ips})")
    
    # ===== UPDATE CHECK COUNT =====
    session["check_count"] = session.get("check_count", 0) + 1
    session["last_check"] = current_time
    sessions[key] = session
    save_sessions(sessions)
    
    # ===== SUCCESS RESPONSE =====
    expire_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(session["expire_at"]))
    
    print(f"[OK] Key {key[:8]}... | IP: {user_ip} | Checks: {session['check_count']} | IPs: {len(ip_list)}/{max_ips}")
    
    return jsonify({
        "status": "ok",
        "msg": "Key hợp lệ",
        "expire_at": expire_str,
        "type": session.get("type", "free"),
        "ips_used": len(ip_list),
        "max_ips": max_ips
    }), 200

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
    <title>ARES Key System</title>
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
        .container {
            max-width: 500px;
            width: 100%;
            background: rgba(255, 255, 255, 0.05);
            border: 2px solid rgba(0, 255, 157, 0.3);
            border-radius: 20px;
            padding: 40px;
            text-align: center;
            box-shadow: 0 0 50px rgba(0, 255, 157, 0.2);
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
            margin-bottom: 30px;
        }
        .get-key-btn {
            background: linear-gradient(135deg, #00ff9d 0%, #00cc7d 100%);
            color: #0a0e27;
            border: none;
            padding: 15px 40px;
            font-size: 18px;
            font-weight: bold;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.3s;
            box-shadow: 0 0 20px rgba(0, 255, 157, 0.3);
        }
        .get-key-btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 30px rgba(0, 255, 157, 0.5);
        }
        .info-box {
            margin-top: 30px;
            padding: 20px;
            background: rgba(255, 193, 7, 0.1);
            border: 2px solid #ffc107;
            border-radius: 12px;
            text-align: left;
        }
        .info-item {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 10px;
            color: rgba(255, 255, 255, 0.9);
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
        <div class="logo">ARES</div>
        <div class="subtitle">LICENSE KEY SYSTEM V2.0</div>
        
        <button class="get-key-btn" onclick="getKey()">Lấy Key Ngay</button>
        
        <div class="info-box">
            <div class="info-item">⏰ Key có hiệu lực 24 giờ</div>
            <div class="info-item">🔒 Chỉ hoạt động trên thiết bị của bạn (max 3 IP)</div>
            <div class="info-item">🎁 Hoàn toàn miễn phí</div>
            <div class="info-item">
                📖 <a href="/huong-dan" class="link">Xem hướng dẫn cài đặt tool →</a>
            </div>
        </div>
    </div>

    <script>
        function getKey() {
            window.location.href = "https://link4m.co/api?api=" + "YOUR_LINK4M_KEY" + "&url=https://webkeyy.vercel.app/success&format=text";
        }
    </script>
</body>
</html>
"""

SUCCESS_HTML = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Key của bạn - ARES</title>
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
        .container {
            max-width: 600px;
            width: 100%;
            background: rgba(255, 255, 255, 0.05);
            border: 2px solid rgba(0, 255, 157, 0.3);
            border-radius: 20px;
            padding: 40px;
            text-align: center;
        }
        .success-icon {
            font-size: 64px;
            margin-bottom: 20px;
        }
        h1 {
            color: #00ff9d;
            margin-bottom: 20px;
        }
        .key-box {
            background: #1e293b;
            border: 2px solid #00ff9d;
            border-radius: 12px;
            padding: 20px;
            margin: 20px 0;
            word-break: break-all;
            font-family: 'Courier New', monospace;
            font-size: 18px;
            color: #00ff9d;
        }
        .copy-btn {
            background: #00ff9d;
            color: #0a0e27;
            border: none;
            padding: 12px 30px;
            border-radius: 8px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
            margin-top: 15px;
        }
        .copy-btn:hover {
            background: #00cc7d;
            transform: scale(1.05);
        }
        .expire-info {
            margin-top: 20px;
            color: #ffc107;
        }
        .note {
            margin-top: 30px;
            padding: 20px;
            background: rgba(255, 193, 7, 0.1);
            border: 2px solid #ffc107;
            border-radius: 12px;
            text-align: left;
        }
        .note-item {
            margin-bottom: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="success-icon">✅</div>
        <h1>Key của bạn đã sẵn sàng!</h1>
        
        <div class="key-box" id="keyBox">{{ key }}</div>
        
        <button class="copy-btn" onclick="copyKey()">📋 Copy Key</button>
        
        <div class="expire-info">
            ⏰ Key hết hạn: {{ expire_time }}
        </div>
        
        <div class="note">
            <div class="note-item">✅ Key có hiệu lực 24 giờ</div>
            <div class="note-item">✅ Cho phép đổi IP tối đa 3 lần (4G OK)</div>
            <div class="note-item">❌ Không chia sẻ key cho người khác</div>
            <div class="note-item">🔄 Lấy key mới sau 24 giờ</div>
        </div>
    </div>

    <script>
        function copyKey() {
            const key = document.getElementById('keyBox').textContent;
            navigator.clipboard.writeText(key).then(() => {
                alert('✅ Đã copy key vào clipboard!');
            }).catch(() => {
                alert('Vui lòng copy thủ công!');
            });
        }
    </script>
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

# ==================== MAIN ====================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
