from flask import Flask, request, jsonify
import requests
import secrets
import string
import time
import json
import os
from datetime import datetime

app = Flask(__name__)

# Lấy API key từ environment
LINK4M_KEY = os.environ.get('LINK4M_KEY', '')
DATA_FILE = '/tmp/sessions.json'

# ==================== HELPER FUNCTIONS ====================

def load_data():
    """Load sessions từ file JSON"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {"sessions": {}, "keys": {}}

def save_data(data):
    """Lưu sessions vào file JSON"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[ERROR] save_data: {e}")

def cleanup_old_sessions():
    """Xóa sessions và keys hết hạn (24 giờ)"""
    data = load_data()
    now = time.time()
    expired = []
    
    for token, session in data["sessions"].items():
        if now - session.get("created_at", 0) > 86400:
            expired.append(token)
    
    for token in expired:
        key = data["sessions"][token].get("unique_key")
        del data["sessions"][token]
        if key in data["keys"]:
            del data["keys"][key]
    
    if expired:
        save_data(data)
        print(f"[CLEANUP] Xóa {len(expired)} sessions")

def generate_session_token():
    return secrets.token_urlsafe(32)

def generate_key():
    chars = string.ascii_uppercase + string.digits
    return 'ARES-' + ''.join(secrets.choice(chars) for _ in range(16))

# ==================== HTML TEMPLATES ====================

def render_index(link=None):
    """HTML trang chủ"""
    link_html = ""
    if link:
        link_html = f'''
        <div class="success-box">
            <h2>✅ Link của bạn đã sẵn sàng!</h2>
            <p>Vui lòng vượt link bên dưới để nhận License Key:</p>
            <div class="link-box">
                <input type="text" id="linkInput" value="{link}" readonly>
                <button onclick="copyLink()" class="btn-copy">📋 Copy</button>
            </div>
            <a href="{link}" target="_blank" class="btn-primary">🔗 Mở Link</a>
        </div>
        '''
    else:
        link_html = '''
        <div class="main-box">
            <h2>Nhận License Key 24h</h2>
            <p>Nhấn nút bên dưới để nhận link lấy License Key miễn phí</p>
            <form method="POST" action="/get_key">
                <button type="submit" class="btn-primary">🔑 Lấy License Key</button>
            </form>
        </div>
        '''
    
    return f'''
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ARES Tool V23 - License System</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%);
            color: #ffffff;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }}
        .container {{ max-width: 600px; width: 100%; }}
        .banner {{
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: rgba(0, 255, 157, 0.1);
            border: 2px solid #00ff9d;
            border-radius: 10px;
        }}
        .ares-title {{
            font-size: 48px;
            font-weight: bold;
            color: #00ff9d;
            text-shadow: 0 0 20px #00ff9d;
            letter-spacing: 8px;
        }}
        .subtitle {{
            font-size: 14px;
            color: #ffc107;
            margin-top: 5px;
            letter-spacing: 2px;
        }}
        .main-box, .success-box {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(0, 255, 157, 0.3);
            border-radius: 10px;
            padding: 30px;
            margin-bottom: 20px;
            text-align: center;
        }}
        .main-box h2, .success-box h2 {{ color: #00ff9d; margin-bottom: 15px; }}
        .main-box p, .success-box p {{ color: #cccccc; margin-bottom: 20px; }}
        .btn-primary {{
            display: inline-block;
            background: linear-gradient(135deg, #00ff9d 0%, #00cc7a 100%);
            color: #0a0e27;
            padding: 15px 40px;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            text-decoration: none;
            transition: all 0.3s;
        }}
        .btn-primary:hover {{
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(0, 255, 157, 0.4);
        }}
        .link-box {{
            display: flex;
            gap: 10px;
            margin: 20px 0;
        }}
        .link-box input {{
            flex: 1;
            padding: 12px;
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid #00ff9d;
            border-radius: 5px;
            color: #00ff9d;
            font-family: monospace;
        }}
        .btn-copy {{
            background: #ffc107;
            color: #0a0e27;
            padding: 12px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
        }}
        .info-box {{
            background: rgba(0, 0, 0, 0.2);
            border: 1px solid rgba(255, 193, 7, 0.3);
            border-radius: 10px;
            padding: 20px;
        }}
        .info-box h3 {{ color: #ffc107; margin-bottom: 15px; }}
        .info-box ul {{ list-style: none; text-align: left; }}
        .info-box li {{ padding: 8px 0; color: #cccccc; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="banner">
            <h1 class="ares-title">ARES</h1>
            <p class="subtitle">TOOL V23 - LICENSE SYSTEM</p>
        </div>

        {link_html}

        <div class="info-box">
            <h3>📋 Thông tin</h3>
            <ul>
                <li>✅ License Key có hiệu lực <strong>24 giờ</strong></li>
                <li>✅ Tối đa <strong>3 địa chỉ IP</strong> khác nhau (hỗ trợ 4G)</li>
                <li>✅ Rate limit: <strong>10 lần kiểm tra/phút</strong></li>
                <li>❌ Không chia sẻ key cho người khác</li>
            </ul>
        </div>
    </div>
    <script>
        function copyLink() {{
            const input = document.getElementById('linkInput');
            input.select();
            document.execCommand('copy');
            alert('Đã copy link!');
        }}
    </script>
</body>
</html>
    '''

def render_display_key(key, expires_at):
    """HTML hiển thị key"""
    return f'''
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Your License Key - ARES Tool V23</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%);
            color: #ffffff;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }}
        .container {{ max-width: 600px; width: 100%; }}
        .banner {{
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: rgba(0, 255, 157, 0.1);
            border: 2px solid #00ff9d;
            border-radius: 10px;
        }}
        .ares-title {{
            font-size: 48px;
            font-weight: bold;
            color: #00ff9d;
            text-shadow: 0 0 20px #00ff9d;
            letter-spacing: 8px;
        }}
        .subtitle {{ font-size: 14px; color: #ffc107; margin-top: 5px; letter-spacing: 2px; }}
        .success-box {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(0, 255, 157, 0.3);
            border-radius: 10px;
            padding: 30px;
            text-align: center;
        }}
        .success-box h2 {{ color: #00ff9d; margin-bottom: 15px; }}
        .key-display {{ display: flex; gap: 10px; margin: 20px 0; }}
        .key-display input {{
            flex: 1;
            padding: 12px;
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid #00ff9d;
            border-radius: 5px;
            color: #00ff9d;
            font-family: monospace;
            font-size: 16px;
        }}
        .btn-copy {{
            background: #ffc107;
            color: #0a0e27;
            padding: 12px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
        }}
        .info-box {{
            background: rgba(0, 0, 0, 0.2);
            border: 1px solid rgba(255, 193, 7, 0.3);
            border-radius: 10px;
            padding: 20px;
            margin-top: 20px;
        }}
        .info-box h3 {{ color: #ffc107; margin-bottom: 15px; }}
        .info-box ul {{ list-style: none; text-align: left; }}
        .info-box li {{ padding: 8px 0; color: #cccccc; }}
        .info-box code {{
            background: rgba(0, 255, 157, 0.2);
            padding: 2px 8px;
            border-radius: 3px;
            color: #00ff9d;
            font-family: monospace;
        }}
        .warning {{ color: #ff5252; margin-top: 20px; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="banner">
            <h1 class="ares-title">ARES</h1>
            <p class="subtitle">TOOL V23 - LICENSE SYSTEM</p>
        </div>

        <div class="success-box">
            <h2>🎉 License Key của bạn</h2>
            <div class="key-display">
                <input type="text" id="keyInput" value="{key}" readonly>
                <button onclick="copyKey()" class="btn-copy">📋 Copy Key</button>
            </div>
            
            <div class="info-box">
                <h3>⏰ Thông tin Key</h3>
                <ul>
                    <li>🔑 Key: <code>{key}</code></li>
                    <li>⏳ Hết hạn: <strong>{expires_at}</strong></li>
                    <li>📍 Tối đa: <strong>3 IP khác nhau</strong></li>
                </ul>
            </div>

            <p class="warning">⚠️ Lưu lại key này! Trang sẽ không hiển thị lại.</p>
        </div>
    </div>
    <script>
        function copyKey() {{
            const input = document.getElementById('keyInput');
            input.select();
            document.execCommand('copy');
            alert('Đã copy License Key!');
        }}
    </script>
</body>
</html>
    '''

def render_error(error):
    """HTML trang lỗi"""
    return f'''
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lỗi - ARES Tool V23</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%);
            color: #ffffff;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }}
        .container {{ max-width: 600px; width: 100%; text-align: center; }}
        .banner {{
            margin-bottom: 30px;
            padding: 20px;
            background: rgba(0, 255, 157, 0.1);
            border: 2px solid #00ff9d;
            border-radius: 10px;
        }}
        .ares-title {{
            font-size: 48px;
            font-weight: bold;
            color: #00ff9d;
            text-shadow: 0 0 20px #00ff9d;
            letter-spacing: 8px;
        }}
        .subtitle {{ font-size: 14px; color: #ffc107; margin-top: 5px; letter-spacing: 2px; }}
        .error-box {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 82, 82, 0.3);
            border-radius: 10px;
            padding: 30px;
        }}
        .error-box h2 {{ color: #ff5252; margin-bottom: 15px; }}
        .error-box p {{ color: #cccccc; margin-bottom: 20px; }}
        .btn-primary {{
            display: inline-block;
            background: linear-gradient(135deg, #00ff9d 0%, #00cc7a 100%);
            color: #0a0e27;
            padding: 15px 40px;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            font-weight: bold;
            text-decoration: none;
            transition: all 0.3s;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="banner">
            <h1 class="ares-title">ARES</h1>
            <p class="subtitle">TOOL V23 - LICENSE SYSTEM</p>
        </div>
        <div class="error-box">
            <h2>❌ Lỗi</h2>
            <p>{error}</p>
            <a href="/" class="btn-primary">🏠 Quay lại trang chủ</a>
        </div>
    </div>
</body>
</html>
    '''

# ==================== ROUTES ====================

@app.route("/")
def index():
    """Trang chủ"""
    cleanup_old_sessions()
    return render_index()

@app.route("/get_key", methods=['POST'])
def get_key():
    """Tạo link Link4m cho user"""
    if not LINK4M_KEY:
        return render_error("Hệ thống chưa được cấu hình. Vui lòng thử lại sau.")
    
    cleanup_old_sessions()
    
    session_token = generate_session_token()
    unique_key = generate_key()
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent', 'Unknown')
    
    # URL đích - trang hiển thị key
    destination_url = f"https://areskey.vercel.app/k/{session_token}"
    
    try:
        # ✅ GỌI API LINK4M
        api_url = f"https://link4m.co/st?api={LINK4M_KEY}&url={destination_url}"
        
        print(f"[INFO] Gọi Link4m API: {api_url}")
        
        # Headers giả browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://link4m.co/'
        }
        
        # Gọi API
        response = requests.get(api_url, headers=headers, timeout=15)
        
        print(f"[DEBUG] Status Code: {response.status_code}")
        print(f"[DEBUG] Response (first 300 chars): {response.text[:300]}")
        
        # Lấy link rút gọn
        short_url = response.text.strip()
        
        # Kiểm tra response có phải HTML (lỗi Cloudflare)
        if short_url.startswith('<!DOCTYPE') or '<html' in short_url.lower():
            print(f"[ERROR] Link4m trả về HTML (Cloudflare block)")
            # Fallback: dùng link trực tiếp
            short_url = destination_url
            print(f"[FALLBACK] Sử dụng link trực tiếp")
        
        # Kiểm tra link hợp lệ
        elif not short_url.startswith('http'):
            print(f"[ERROR] Link4m response không hợp lệ: {short_url}")
            # Fallback: dùng link trực tiếp
            short_url = destination_url
            print(f"[FALLBACK] Sử dụng link trực tiếp")
        
        print(f"[SUCCESS] Final URL: {short_url}")
        
        # Lưu session vào database
        data = load_data()
        data["sessions"][session_token] = {
            "unique_key": unique_key,
            "created_at": time.time(),
            "verified": False,
            "owner_ip": user_ip,
            "owner_user_agent": user_agent
        }
        
        # Lưu key info
        data["keys"][unique_key] = {
            "created_at": time.time(),
            "ip_list": [],
            "max_ips": 3,
            "check_count": 0,
            "last_check_time": time.time(),
            "session_token": session_token
        }
        
        save_data(data)
        
        print(f"[GET_KEY] Token: {session_token[:8]}... | Key: {unique_key} | IP: {user_ip}")
        
        # Trả về trang hiển thị link
        return render_index(link=short_url)
        
    except requests.exceptions.Timeout:
        print(f"[ERROR] Link4m timeout")
        return render_error("Link4m không phản hồi. Vui lòng thử lại sau.")
    
    except requests.exceptions.ConnectionError:
        print(f"[ERROR] Cannot connect to Link4m")
        return render_error("Không thể kết nối Link4m. Vui lòng thử lại sau.")
    
    except Exception as e:
        print(f"[ERROR] get_key exception: {str(e)}")
        return render_error(f"Lỗi hệ thống: {str(e)}")

@app.route("/k/<token>")
def display_key(token):
    """Hiển thị key sau khi user vượt link"""
    cleanup_old_sessions()
    
    data = load_data()
    
    if token not in data["sessions"]:
        return render_error("Link không hợp lệ hoặc đã hết hạn.")
    
    session = data["sessions"][token]
    unique_key = session["unique_key"]
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    
    # Đánh dấu session đã verified
    if not session.get("verified"):
        session["verified"] = True
        session["verified_at"] = time.time()
        session["verified_ip"] = user_ip
    
    # Thêm IP vào key info
    if unique_key in data["keys"]:
        key_info = data["keys"][unique_key]
        if user_ip not in key_info["ip_list"]:
            key_info["ip_list"].append(user_ip)
    
    save_data(data)
    
    # Tính thời gian hết hạn
    expires_at = datetime.fromtimestamp(session["created_at"] + 86400)
    
    print(f"[DISPLAY_KEY] Token: {token[:8]}... | Key: {unique_key} | IP: {user_ip}")
    
    return render_display_key(unique_key, expires_at.strftime('%d/%m/%Y %H:%M:%S'))

@app.route("/api/check_key", methods=['POST'])
def check_key():
    """API kiểm tra key hợp lệ"""
    cleanup_old_sessions()
    
    try:
        req_data = request.get_json()
        key = req_data.get('key', '')
        user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        
        data = load_data()
        
        if key not in data["keys"]:
            return jsonify({"valid": False, "msg": "Key không tồn tại"})
        
        key_info = data["keys"][key]
        
        # Rate limit
        now = time.time()
        if now - key_info.get("last_check_time", 0) > 60:
            key_info["check_count"] = 0
            key_info["last_check_time"] = now
        
        if key_info["check_count"] >= 10:
            save_data(data)
            return jsonify({"valid": False, "msg": "Rate limit: Tối đa 10 lần/phút"})
        
        key_info["check_count"] += 1
        
        # IP tracking
        if user_ip not in key_info["ip_list"]:
            if len(key_info["ip_list"]) >= key_info["max_ips"]:
                save_data(data)
                return jsonify({"valid": False, "msg": f"Key đã đạt tối đa {key_info['max_ips']} IP"})
            key_info["ip_list"].append(user_ip)
        
        save_data(data)
        
        return jsonify({
            "valid": True,
            "msg": "Key hợp lệ",
            "key": key,
            "ip_count": len(key_info["ip_list"]),
            "max_ips": key_info["max_ips"]
        })
        
    except Exception as e:
        print(f"[ERROR] check_key: {e}")
        return jsonify({"valid": False, "msg": f"Lỗi: {str(e)}"})

if __name__ == "__main__":
    app.run(debug=True)
