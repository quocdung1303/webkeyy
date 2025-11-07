from flask import Flask, request
import requests
import secrets
import string
import time
import json
import os
from datetime import datetime

app = Flask(__name__)

LINK4M_KEY = os.environ.get('LINK4M_KEY', '6906d12068643654b40df4e9')
DATA_FILE = '/tmp/keys.json'

# ==================== HELPERS ====================

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"keys": {}}

def save_data(data):
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f)
    except:
        pass

def cleanup():
    data = load_data()
    now = time.time()
    expired = [k for k, v in data["keys"].items() if now - v.get("created_at", 0) > 86400]
    for k in expired:
        del data["keys"][k]
    if expired:
        save_data(data)

def gen_token():
    return secrets.token_urlsafe(32)

def gen_key():
    return 'ARES-' + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(16))

# ==================== ROUTES ====================

@app.route("/")
def index():
    cleanup()
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
        }
        .subtitle { font-size: 13px; color: #ffc107; letter-spacing: 3px; }
        .box {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(0, 255, 157, 0.3);
            border-radius: 15px;
            padding: 40px;
            text-align: center;
        }
        h2 { color: #00ff9d; margin-bottom: 15px; }
        p { color: #ccc; margin-bottom: 25px; }
        .btn {
            background: linear-gradient(135deg, #00ff9d, #00cc7a);
            color: #0a0e27;
            padding: 18px 50px;
            border: none;
            border-radius: 8px;
            font-size: 18px;
            font-weight: bold;
            cursor: pointer;
        }
        .info {
            background: rgba(0, 0, 0, 0.2);
            border: 1px solid rgba(255, 193, 7, 0.3);
            border-radius: 10px;
            padding: 25px;
            margin-top: 25px;
        }
        .info h3 { color: #ffc107; margin-bottom: 15px; }
        .info ul { list-style: none; text-align: left; }
        .info li { padding: 10px 0; color: #ccc; }
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
            <p>Nhấn nút để nhận link lấy License Key</p>
            <form method="POST" action="/get_link">
                <button type="submit" class="btn">Lấy License Key</button>
            </form>
        </div>
        <div class="info">
            <h3>📋 Thông tin</h3>
            <ul>
                <li>✅ Key hiệu lực <strong>24 giờ</strong></li>
                <li>✅ Tối đa <strong>3 IP</strong></li>
                <li>✅ Rate limit: <strong>10 lần/phút</strong></li>
            </ul>
        </div>
    </div>
</body>
</html>
    '''

@app.route("/get_link", methods=['POST'])
def get_link():
    cleanup()
    
    token = gen_token()
    key = gen_key()
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    
    # Lưu key
    data = load_data()
    data["keys"][token] = {
        "key": key,
        "created_at": time.time(),
        "ip_list": [ip],
        "max_ips": 3
    }
    save_data(data)
    
    # URL đích
    dest = f"https://areskey.vercel.app/key/{token}"
    
    # Gọi Link4m
    try:
        link4m_url = f"https://link4m.co/st?api={LINK4M_KEY}&url={dest}"
        resp = requests.get(link4m_url, timeout=10)
        short = resp.text.strip()
        
        if not short.startswith('http'):
            short = dest
        
        return f'''
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Link - ARES</title>
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
        }}
        .subtitle {{ font-size: 13px; color: #ffc107; letter-spacing: 3px; }}
        .box {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(0, 255, 157, 0.3);
            border-radius: 15px;
            padding: 40px;
            text-align: center;
        }}
        h2 {{ color: #00ff9d; margin-bottom: 15px; }}
        p {{ color: #ccc; margin-bottom: 25px; }}
        .link-box {{ display: flex; gap: 10px; margin: 25px 0; }}
        .link-box input {{
            flex: 1;
            padding: 15px;
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid #00ff9d;
            border-radius: 8px;
            color: #00ff9d;
            font-family: monospace;
        }}
        .btn {{
            background: linear-gradient(135deg, #00ff9d, #00cc7a);
            color: #0a0e27;
            padding: 18px 50px;
            border: none;
            border-radius: 8px;
            font-size: 18px;
            font-weight: bold;
            text-decoration: none;
            display: inline-block;
        }}
        .btn-copy {{ background: #ffc107; padding: 15px 25px; cursor: pointer; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="banner">
            <h1>ARES</h1>
            <div class="subtitle">TOOL V23 - LICENSE SYSTEM</div>
        </div>
        <div class="box">
            <h2>✅ Link của bạn</h2>
            <p>Vượt link để nhận key:</p>
            <div class="link-box">
                <input id="link" value="{short}" readonly>
                <button class="btn-copy" onclick="copy()">📋</button>
            </div>
            <a href="{short}" target="_blank" class="btn">🔗 Mở Link</a>
        </div>
    </div>
    <script>
        function copy() {{
            document.getElementById('link').select();
            document.execCommand('copy');
            alert('Đã copy!');
        }}
    </script>
</body>
</html>
        '''
    except Exception as e:
        return f'<h1 style="color:#fff;text-align:center;padding:50px;">Lỗi: {e}</h1>'

@app.route("/key/<token>")
def show_key(token):
    cleanup()
    
    data = load_data()
    if token not in data["keys"]:
        return '<h1 style="color:#fff;text-align:center;padding:50px;">❌ Link không hợp lệ</h1>'
    
    info = data["keys"][token]
    key = info["key"]
    expires = datetime.fromtimestamp(info["created_at"] + 86400).strftime('%d/%m/%Y %H:%M')
    
    return f'''
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Key - ARES</title>
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
        }}
        .subtitle {{ font-size: 13px; color: #ffc107; letter-spacing: 3px; }}
        .box {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(0, 255, 157, 0.3);
            border-radius: 15px;
            padding: 40px;
            text-align: center;
        }}
        h2 {{ color: #00ff9d; margin-bottom: 20px; }}
        .key-box {{ display: flex; gap: 10px; margin: 25px 0; }}
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
            <h2>🎉 License Key</h2>
            <div class="key-box">
                <input id="key" value="{key}" readonly>
                <button class="btn-copy" onclick="copy()">📋</button>
            </div>
            <div class="info">
                <h3>⏰ Thông tin</h3>
                <ul>
                    <li>🔑 Key: <strong>{key}</strong></li>
                    <li>⏳ Hết hạn: <strong>{expires}</strong></li>
                    <li>📍 Max: <strong>3 IP</strong></li>
                </ul>
            </div>
            <p class="warn">⚠️ Lưu lại key!</p>
        </div>
    </div>
    <script>
        function copy() {{
            document.getElementById('key').select();
            document.execCommand('copy');
            alert('Đã copy!');
        }}
    </script>
</body>
</html>
    '''

if __name__ == "__main__":
    app.run(debug=True)
