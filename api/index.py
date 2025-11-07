from flask import Flask, request
import requests
import secrets
import string
import time
import json
import os

app = Flask(__name__)

LINK4M_KEY = os.environ.get('LINK4M_KEY', '6906d12068643654b40df4e9')
DATA_FILE = '/tmp/keys.json'

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

def gen_token():
    return secrets.token_urlsafe(32)

def gen_key():
    return 'ARES-' + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(16))

@app.route("/")
def index():
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
            <form method="POST" action="/get_link">
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

@app.route("/get_link", methods=['POST'])
def get_link():
    token = gen_token()
    key = gen_key()
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    
    # Lưu key vào data
    data = load_data()
    data["keys"][token] = {
        "key": key,
        "created_at": time.time(),
        "ip_list": [ip],
        "max_ips": 3
    }
    save_data(data)
    
    # URL đích - Trang 2 hiển thị key
    destination = f"https://areskey-display.vercel.app/?token={token}"
    
    # Gọi Link4m
    try:
        link4m_url = f"https://link4m.co/st?api={LINK4M_KEY}&url={destination}"
        resp = requests.get(link4m_url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        short = resp.text.strip()
        
        # Validate
        if not short.startswith('http'):
            short = destination
        
        print(f"[GET_LINK] Token: {token} | Key: {key} | Link: {short}")
        
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
            <p>Vui lòng vượt link để nhận License Key:</p>
            <div class="link-box">
                <input type="text" id="link" value="{short}" readonly>
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
        return f'<h1 style="color:#fff;">Lỗi: {e}</h1>'

@app.route("/api/get_key/<token>")
def api_get_key(token):
    """API cho trang 2 lấy key"""
    data = load_data()
    if token in data["keys"]:
        return data["keys"][token]
    return {"error": "Token không hợp lệ"}

if __name__ == "__main__":
    app.run(debug=True)
