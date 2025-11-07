from flask import Flask, request, jsonify
import requests
import secrets
import string
import time
import json
import os
from datetime import datetime

app = Flask(__name__)

# Config
LINK4M_KEY = os.environ.get('LINK4M_KEY', '6906d12068643654b40df4e9')
DATA_FILE = '/tmp/sessions.json'

# ==================== HELPER FUNCTIONS ====================

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"sessions": {}, "keys": {}}

def save_data(data):
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[ERROR] save_data: {e}")

def cleanup_old():
    data = load_data()
    now = time.time()
    expired = [t for t, s in data["sessions"].items() if now - s.get("created_at", 0) > 86400]
    for t in expired:
        key = data["sessions"][t].get("unique_key")
        del data["sessions"][t]
        if key in data["keys"]:
            del data["keys"][key]
    if expired:
        save_data(data)

def gen_token():
    return secrets.token_urlsafe(32)

def gen_key():
    return 'ARES-' + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(16))

# ==================== ROUTES ====================

@app.route("/")
def index():
    cleanup_old()
    return '''
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ARES Tool V23 - License System</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%);
            color: #fff;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container { max-width: 500px; width: 100%; }
        .banner {
            text-align: center;
            margin-bottom: 30px;
            padding: 30px;
            background: rgba(0, 255, 157, 0.1);
            border: 2px solid #00ff9d;
            border-radius: 15px;
        }
        h1 {
            font-size: 56px;
            color: #00ff9d;
            text-shadow: 0 0 30px #00ff9d;
            letter-spacing: 12px;
            margin-bottom: 10px;
        }
        .subtitle {
            font-size: 13px;
            color: #ffc107;
            letter-spacing: 3px;
        }
        .box {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(0, 255, 157, 0.3);
            border-radius: 15px;
            padding: 40px;
            text-align: center;
        }
        h2 { color: #00ff9d; margin-bottom: 15px; font-size: 24px; }
        p { color: #ccc; margin-bottom: 25px; line-height: 1.6; }
        .btn {
            background: linear-gradient(135deg, #00ff9d, #00cc7a);
            color: #0a0e27;
            padding: 18px 50px;
            border: none;
            border-radius: 8px;
            font-size: 18px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
            text-decoration: none;
            display: inline-block;
        }
        .btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 25px rgba(0, 255, 157, 0.5);
        }
        .info {
            background: rgba(0, 0, 0, 0.2);
            border: 1px solid rgba(255, 193, 7, 0.3);
            border-radius: 10px;
            padding: 25px;
            margin-top: 25px;
        }
        .info h3 { color: #ffc107; margin-bottom: 15px; font-size: 18px; }
        .info ul { list-style: none; text-align: left; }
        .info li { padding: 10px 0; color: #ccc; font-size: 15px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="banner">
            <h1>ARES</h1>
            <div class="subtitle">TOOL V23 - LICENSE SYSTEM</div>
        </div>
        <div class="box">
            <h2>🔑 Nhận License Key 24h</h2>
            <p>Nhấn nút bên dưới để nhận link lấy License Key miễn phí</p>
            <form method="POST" action="/get_key">
                <button type="submit" class="btn">Lấy License Key</button>
            </form>
        </div>
        <div class="info">
            <h3>📋 Thông tin</h3>
            <ul>
                <li>✅ License Key có hiệu lực <strong>24 giờ</strong></li>
                <li>✅ Tối đa <strong>3 địa chỉ IP</strong> khác nhau</li>
                <li>✅ Rate limit: <strong>10 lần/phút</strong></li>
                <li>❌ Không chia sẻ key cho người khác</li>
            </ul>
        </div>
    </div>
</body>
</html>
    '''

@app.route("/get_key", methods=['POST'])
def get_key():
    cleanup_old()
    
    token = gen_token()
    key = gen_key()
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    
    dest = f"https://areskey.vercel.app/k/{token}"
    
    # Gọi Link4m
    link4m_url = f"https://link4m.co/st?api={LINK4M_KEY}&url={dest}"
    
    try:
        resp = requests.get(link4m_url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        short = resp.text.strip()
        
        # Nếu lỗi → dùng link trực tiếp
        if not short.startswith('http') or 'html' in short.lower():
            short = dest
        
        # Lưu data
        data = load_data()
        data["sessions"][token] = {
            "unique_key": key,
            "created_at": time.time(),
            "verified": False,
            "owner_ip": ip
        }
        data["keys"][key] = {
            "created_at": time.time(),
            "ip_list": [],
            "max_ips": 3,
            "check_count": 0,
            "last_check": time.time()
        }
        save_data(data)
        
        return f'''
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Link của bạn - ARES</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%);
            color: #fff;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }}
        .container {{ max-width: 500px; width: 100%; }}
        .banner {{
            text-align: center;
            margin-bottom: 30px;
            padding: 30px;
            background: rgba(0, 255, 157, 0.1);
            border: 2px solid #00ff9d;
            border-radius: 15px;
        }}
        h1 {{
            font-size: 56px;
            color: #00ff9d;
            text-shadow: 0 0 30px #00ff9d;
            letter-spacing: 12px;
            margin-bottom: 10px;
        }}
        .subtitle {{
            font-size: 13px;
            color: #ffc107;
            letter-spacing: 3px;
        }}
        .box {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(0, 255, 157, 0.3);
            border-radius: 15px;
            padding: 40px;
            text-align: center;
        }}
        h2 {{ color: #00ff9d; margin-bottom: 15px; font-size: 24px; }}
        p {{ color: #ccc; margin-bottom: 25px; line-height: 1.6; }}
        .link-box {{
            display: flex;
            gap: 10px;
            margin: 25px 0;
        }}
        .link-box input {{
            flex: 1;
            padding: 15px;
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid #00ff9d;
            border-radius: 8px;
            color: #00ff9d;
            font-family: monospace;
            font-size: 14px;
        }}
        .btn {{
            background: linear-gradient(135deg, #00ff9d, #00cc7a);
            color: #0a0e27;
            padding: 18px 50px;
            border: none;
            border-radius: 8px;
            font-size: 18px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
            text-decoration: none;
            display: inline-block;
        }}
        .btn:hover {{
            transform: translateY(-3px);
            box-shadow: 0 8px 25px rgba(0, 255, 157, 0.5);
        }}
        .btn-copy {{
            background: #ffc107;
            padding: 15px 25px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="banner">
            <h1>ARES</h1>
            <div class="subtitle">TOOL V23 - LICENSE SYSTEM</div>
        </div>
        <div class="box">
            <h2>✅ Link của bạn đã sẵn sàng!</h2>
            <p>Vui lòng vượt link bên dưới để nhận License Key:</p>
            <div class="link-box">
                <input type="text" id="link" value="{short}" readonly>
                <button class="btn btn-copy" onclick="copy()">📋 Copy</button>
            </div>
            <a href="{short}" target="_blank" class="btn">🔗 Mở Link</a>
        </div>
    </div>
    <script>
        function copy() {{
            document.getElementById('link').select();
            document.execCommand('copy');
            alert('Đã copy link!');
        }}
    </script>
</body>
</html>
        '''
    except Exception as e:
        return f'<h1>Lỗi: {e}</h1>'

@app.route("/k/<token>")
def show_key(token):
    cleanup_old()
    
    data = load_data()
    if token not in data["sessions"]:
        return '<h1>Link không hợp lệ hoặc đã hết hạn</h1>'
    
    session = data["sessions"][token]
    key = session["unique_key"]
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    
    # Đánh dấu verified
    if not session.get("verified"):
        session["verified"] = True
        session["verified_at"] = time.time()
    
    # Thêm IP
    if key in data["keys"]:
        if ip not in data["keys"][key]["ip_list"]:
            data["keys"][key]["ip_list"].append(ip)
    
    save_data(data)
    
    expires = datetime.fromtimestamp(session["created_at"] + 86400).strftime('%d/%m/%Y %H:%M')
    
    return f'''
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>License Key - ARES</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%);
            color: #fff;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }}
        .container {{ max-width: 500px; width: 100%; }}
        .banner {{
            text-align: center;
            margin-bottom: 30px;
            padding: 30px;
            background: rgba(0, 255, 157, 0.1);
            border: 2px solid #00ff9d;
            border-radius: 15px;
        }}
        h1 {{
            font-size: 56px;
            color: #00ff9d;
            text-shadow: 0 0 30px #00ff9d;
            letter-spacing: 12px;
            margin-bottom: 10px;
        }}
        .subtitle {{
            font-size: 13px;
            color: #ffc107;
            letter-spacing: 3px;
        }}
        .box {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(0, 255, 157, 0.3);
            border-radius: 15px;
            padding: 40px;
            text-align: center;
        }}
        h2 {{ color: #00ff9d; margin-bottom: 20px; font-size: 28px; }}
        .key-box {{
            display: flex;
            gap: 10px;
            margin: 25px 0;
        }}
        .key-box input {{
            flex: 1;
            padding: 18px;
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid #00ff9d;
            border-radius: 8px;
            color: #00ff9d;
            font-family: monospace;
            font-size: 16px;
            font-weight: bold;
        }}
        .btn-copy {{
            background: #ffc107;
            color: #0a0e27;
            padding: 18px 30px;
            border: none;
            border-radius: 8px;
            font-weight: bold;
            cursor: pointer;
        }}
        .info {{
            background: rgba(0, 0, 0, 0.2);
            border: 1px solid rgba(255, 193, 7, 0.3);
            border-radius: 10px;
            padding: 25px;
            margin-top: 25px;
        }}
        .info h3 {{ color: #ffc107; margin-bottom: 15px; }}
        .info ul {{ list-style: none; text-align: left; }}
        .info li {{ padding: 10px 0; color: #ccc; }}
        .warn {{ color: #ff5252; margin-top: 20px; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="banner">
            <h1>ARES</h1>
            <div class="subtitle">TOOL V23 - LICENSE SYSTEM</div>
        </div>
        <div class="box">
            <h2>🎉 License Key của bạn</h2>
            <div class="key-box">
                <input type="text" id="key" value="{key}" readonly>
                <button class="btn-copy" onclick="copy()">📋 Copy</button>
            </div>
            <div class="info">
                <h3>⏰ Thông tin Key</h3>
                <ul>
                    <li>🔑 Key: <strong>{key}</strong></li>
                    <li>⏳ Hết hạn: <strong>{expires}</strong></li>
                    <li>📍 Tối đa: <strong>3 IP khác nhau</strong></li>
                </ul>
            </div>
            <p class="warn">⚠️ Lưu lại key này! Trang sẽ không hiển thị lại.</p>
        </div>
    </div>
    <script>
        function copy() {{
            document.getElementById('key').select();
            document.execCommand('copy');
            alert('Đã copy License Key!');
        }}
    </script>
</body>
</html>
    '''

@app.route("/api/check_key", methods=['POST'])
def check_key():
    cleanup_old()
    
    try:
        req = request.get_json()
        key = req.get('key', '')
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        
        data = load_data()
        
        if key not in data["keys"]:
            return jsonify({"valid": False, "msg": "Key không tồn tại"})
        
        k = data["keys"][key]
        
        # Rate limit
        now = time.time()
        if now - k.get("last_check", 0) > 60:
            k["check_count"] = 0
        if k["check_count"] >= 10:
            return jsonify({"valid": False, "msg": "Rate limit: 10 lần/phút"})
        
        k["check_count"] += 1
        k["last_check"] = now
        
        # IP check
        if ip not in k["ip_list"]:
            if len(k["ip_list"]) >= k["max_ips"]:
                return jsonify({"valid": False, "msg": f"Đã đạt max {k['max_ips']} IP"})
            k["ip_list"].append(ip)
        
        save_data(data)
        
        return jsonify({
            "valid": True,
            "msg": "Key hợp lệ",
            "key": key,
            "ip_count": len(k["ip_list"]),
            "max_ips": k["max_ips"]
        })
    except Exception as e:
        return jsonify({"valid": False, "msg": str(e)})

if __name__ == "__main__":
    app.run(debug=True)
