from flask import Flask, request, jsonify, send_from_directory
import requests
import json
import os
import time
import random
import string
import secrets

app = Flask(__name__, static_folder='static')

LINK4M_API = "https://link4m.co/api-shorten/v2"
LINK4M_KEY = os.getenv("LINK4M_KEY")

def get_base_url():
    base_url = os.getenv("BASE_URL", "")
    if base_url:
        return base_url if base_url.startswith("http") else f"https://{base_url}"
    
    replit_domain = os.getenv("REPLIT_DEV_DOMAIN", "")
    if replit_domain:
        return f"https://{replit_domain}"
    
    if request:
        return request.url_root.rstrip('/')
    
    return ""

KEY_FILE = "key.json"

def generate_key(length=24):
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

def generate_session_token():
    return secrets.token_urlsafe(32)

def load_data():
    if not os.path.exists(KEY_FILE):
        return {"date": "", "key": "", "sessions": {}}
    try:
        with open(KEY_FILE, "r") as f:
            data = json.load(f)
            if "sessions" not in data:
                data["sessions"] = {}
            return data
    except:
        return {"date": "", "key": "", "sessions": {}}

def save_data(data):
    with open(KEY_FILE, "w") as f:
        json.dump(data, f, indent=2)

def new_daily_key():
    today = time.strftime("%Y-%m-%d")
    data = load_data()
    
    if data.get("date") != today:
        key = generate_key()
        data = {
            "date": today,
            "key": key,
            "sessions": {}
        }
        save_data(data)
    
    return data

def cleanup_old_sessions():
    data = load_data()
    current_time = time.time()
    sessions_to_delete = []
    
    for session_token, session_data in data.get("sessions", {}).items():
        if current_time - session_data.get("created_at", 0) > 3600:
            sessions_to_delete.append(session_token)
    
    for token in sessions_to_delete:
        del data["sessions"][token]
    
    if sessions_to_delete:
        save_data(data)

@app.route("/")
def home():
    return send_from_directory('static', 'index.html')

@app.route("/api/get_link")
def get_link():
    cleanup_old_sessions()
    data = new_daily_key()
    
    if not LINK4M_KEY:
        return jsonify({"status": "error", "msg": "Chưa cấu hình LINK4M_KEY. Vui lòng thêm secret."})
    
    session_token = generate_session_token()
    verify_secret = generate_session_token()
    
    base_url = get_base_url()
    if not base_url:
        return jsonify({"status": "error", "msg": "Không xác định được BASE_URL"})
    
    destination = f"{base_url}/api/verify?token={session_token}&secret={verify_secret}"
    
    try:
        create_url = f"{LINK4M_API}?api={LINK4M_KEY}&url={destination}"
        res = requests.get(create_url, timeout=10).json()
        
        if res.get("status") != "success" or not res.get("shortenedUrl"):
            return jsonify({"status": "error", "msg": "Không tạo được link rút gọn"})
        
        short_url = res["shortenedUrl"]
        
        data["sessions"][session_token] = {
            "verified": False,
            "verify_secret": verify_secret,
            "created_at": time.time()
        }
        save_data(data)
        
        return jsonify({
            "status": "ok",
            "message": "Vui lòng vượt link để lấy key",
            "url": short_url,
            "token": session_token
        })
    except Exception as e:
        return jsonify({"status": "error", "msg": f"Lỗi kết nối API: {str(e)}"})

@app.route("/api/verify")
def verify():
    session_token = request.args.get("token")
    verify_secret = request.args.get("secret")
    
    if not session_token or not verify_secret:
        return "❌ Thiếu thông tin xác thực"
    
    data = load_data()
    
    if session_token not in data.get("sessions", {}):
        return "❌ Session không tồn tại hoặc đã hết hạn"
    
    session = data["sessions"][session_token]
    
    if session.get("verify_secret") != verify_secret:
        return "❌ Secret không hợp lệ. Vui lòng vượt link đúng cách!"
    
    data["sessions"][session_token]["verified"] = True
    save_data(data)
    
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Xác thực thành công</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                margin: 0;
            }
            .success-box {
                background: white;
                padding: 40px;
                border-radius: 15px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                text-align: center;
                max-width: 400px;
            }
            .checkmark {
                font-size: 80px;
                color: #4CAF50;
                animation: pop 0.5s ease-out;
            }
            @keyframes pop {
                0% { transform: scale(0); }
                50% { transform: scale(1.2); }
                100% { transform: scale(1); }
            }
            h1 { color: #333; margin: 20px 0; }
            p { color: #666; font-size: 16px; }
            .btn {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 12px 30px;
                border-radius: 25px;
                font-size: 16px;
                cursor: pointer;
                margin-top: 20px;
                text-decoration: none;
                display: inline-block;
            }
        </style>
    </head>
    <body>
        <div class="success-box">
            <div class="checkmark">✅</div>
            <h1>Xác thực thành công!</h1>
            <p>Bạn đã vượt link thành công. Vui lòng quay lại trang chủ để lấy key.</p>
            <a href="/" class="btn">Quay lại trang chủ</a>
        </div>
    </body>
    </html>
    """

@app.route("/api/get_key")
def get_key():
    session_token = request.args.get("token")
    
    if not session_token:
        return jsonify({"status": "error", "msg": "Thiếu token"})
    
    data = load_data()
    
    if session_token not in data.get("sessions", {}):
        return jsonify({"status": "error", "msg": "Session không tồn tại hoặc đã hết hạn"})
    
    if not data["sessions"][session_token].get("verified"):
        return jsonify({"status": "error", "msg": "Bạn chưa vượt link. Vui lòng vượt link trước!"})
    
    return jsonify({
        "status": "ok",
        "key": data["key"],
        "date": data["date"]
    })

@app.route("/api/check_key")
def check_key():
    key = request.args.get("key")
    
    if not key:
        return jsonify({"status": "fail", "msg": "Thiếu key"})
    
    data = load_data()
    
    if key == data.get("key"):
        return jsonify({"status": "ok", "msg": "Key hợp lệ", "date": data["date"]})
    
    return jsonify({"status": "fail", "msg": "Key không hợp lệ"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
