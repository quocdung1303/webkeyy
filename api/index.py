from flask import Flask, request, jsonify
import json
import os
import time
import random
import string
import secrets
import requests

app = Flask(__name__)

# ✅ SỬA: Đúng API key và endpoint
LINK4M_KEY = os.getenv("LINK4M_KEY", "6906d12068643654b40df4e9")
KEY_FILE = "/tmp/key.json"

def generate_key(length=24):
    """Tạo key ngẫu nhiên"""
    return 'ARES-' + ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(length))

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
        print(f"[CLEANUP] Đã xóa {len(sessions_to_delete)} session")

@app.before_request
def auto_cleanup():
    """Tự động cleanup"""
    cleanup_old_sessions()

@app.route("/")
def home():
    """Trang chủ"""
    return '''<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔑 ARES - Hệ thống Key</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            max-width: 500px;
            width: 100%;
        }
        h1 { color: #333; text-align: center; margin-bottom: 10px; font-size: 28px; }
        .subtitle { text-align: center; color: #666; margin-bottom: 30px; font-size: 14px; }
        .step {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            border-left: 4px solid #667eea;
        }
        .step-title { font-weight: bold; color: #667eea; margin-bottom: 10px; }
        .step-content { color: #555; font-size: 14px; line-height: 1.6; }
        .btn {
            width: 100%;
            padding: 15px;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
            margin-top: 10px;
        }
        .btn-primary { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
        .btn-success { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); color: white; }
        .btn:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4); }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .link-display { background: #e3f2fd; padding: 20px; border-radius: 10px; margin: 15px 0; display: none; border: 2px solid #2196F3; }
        .link-display.show { display: block; }
        .link-url {
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 25px;
            border-radius: 25px;
            text-decoration: none;
            margin: 10px 0;
            transition: all 0.3s;
            font-weight: bold;
        }
        .link-url:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4); }
        .timer { background: #fff3cd; border: 2px solid #ff9800; border-radius: 10px; padding: 15px; margin: 15px 0; text-align: center; }
        .timer-title { color: #ff6b00; font-weight: bold; font-size: 14px; margin-bottom: 10px; }
        .timer-value { font-size: 32px; font-weight: bold; color: #ff6b00; }
        .key-display { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 20px; border-radius: 10px; margin: 15px 0; text-align: center; display: none; }
        .key-display.show { display: block; }
        .key-value { font-size: 18px; font-weight: bold; letter-spacing: 1px; margin-top: 10px; word-break: break-all; background: rgba(255,255,255,0.2); padding: 15px; border-radius: 8px; }
        .message { padding: 15px; border-radius: 10px; margin: 15px 0; font-size: 14px; display: none; }
        .message.show { display: block; }
        .message.error { background: #fee; color: #c33; border-left: 4px solid #c33; }
        .message.success { background: #efe; color: #3c3; border-left: 4px solid #3c3; }
        .message.info { background: #eef; color: #33c; border-left: 4px solid #33c; }
        .loading { display: none; text-align: center; color: #667eea; margin: 10px 0; }
        .loading.show { display: block; }
        .spinner { border: 3px solid #f3f3f3; border-top: 3px solid #667eea; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 0 auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .footer { text-align: center; margin-top: 20px; color: #888; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔑 ARES - Hệ thống Key</h1>
        <p class="subtitle">Vượt link để nhận key miễn phí</p>
        <div class="step">
            <div class="step-title">📋 Hướng dẫn:</div>
            <div class="step-content">
                1. Nhấn "Lấy Link" để nhận link rút gọn<br>
                2. Nhấn vào link và vượt qua trang quảng cáo<br>
                3. Đợi đủ 15 giây (có đồng hồ đếm ngược)<br>
                4. Nhấn "Lấy Key" để nhận key<br>
                5. Key có hiệu lực 24 giờ
            </div>
        </div>
        <div class="message" id="message"></div>
        <div class="loading" id="loading"><div class="spinner"></div><p>Đang xử lý...</p></div>
        <div class="link-display" id="linkDisplay">
            <div style="text-align: center; margin-bottom: 15px;">
                <span style="font-size: 30px;">✅</span><br>
                <strong style="color: #2196F3; font-size: 16px;">Link sẵn sàng!</strong>
            </div>
            <div style="text-align: center;">
                <a href="#" id="shortLink" target="_blank" class="link-url">🔗 Nhấn vào đây để vượt link</a>
            </div>
            <div class="timer" id="timerBox" style="display:none;">
                <div class="timer-title">⏰ Vui lòng đợi:</div>
                <div class="timer-value" id="timerValue">15</div>
                <div style="font-size: 12px; margin-top: 5px; color: #856404;">giây nữa để lấy key</div>
            </div>
            <p style="text-align: center; color: #666; font-size: 14px; margin-top: 15px;">💡 Sau khi vượt link xong, đợi đồng hồ về 0 rồi nhấn "Lấy Key"</p>
        </div>
        <div class="key-display" id="keyDisplay">
            <p style="font-size: 18px; margin-bottom: 5px;">🎉 Key của bạn:</p>
            <div class="key-value" id="keyValue"></div>
            <p style="font-size: 12px; margin-top: 10px; opacity: 0.9;" id="keyExpire"></p>
        </div>
        <button class="btn btn-primary" id="getLinkBtn" onclick="getLink()">📎 Lấy Link</button>
        <button class="btn btn-success" id="getKeyBtn" onclick="getKey()" disabled>🔑 Lấy Key</button>
        <div class="footer">Key riêng cho từng người • Hiệu lực 24 giờ</div>
    </div>
    <script>
        let sessionToken = localStorage.getItem('sessionToken');
        let countdownInterval = null;
        function showMessage(text, type = 'info') {
            const msgEl = document.getElementById('message');
            msgEl.textContent = text;
            msgEl.className = `message ${type} show`;
            setTimeout(() => msgEl.classList.remove('show'), 5000);
        }
        function showLoading(show) { document.getElementById('loading').classList.toggle('show', show); }
        function startCountdown(seconds) {
            let remaining = seconds;
            document.getElementById('timerBox').style.display = 'block';
            document.getElementById('timerValue').textContent = remaining;
            document.getElementById('getKeyBtn').disabled = true;
            if (countdownInterval) clearInterval(countdownInterval);
            countdownInterval = setInterval(() => {
                remaining--;
                document.getElementById('timerValue').textContent = remaining;
                if (remaining <= 0) {
                    clearInterval(countdownInterval);
                    document.getElementById('timerBox').style.display = 'none';
                    document.getElementById('getKeyBtn').disabled = false;
                    showMessage('✅ Đã đủ thời gian! Bạn có thể nhấn "Lấy Key".', 'success');
                }
            }, 1000);
        }
        async function getLink() {
            showLoading(true);
            document.getElementById('getLinkBtn').disabled = true;
            try {
                const response = await fetch('/api/get_link');
                const data = await response.json();
                if (data.status === 'ok') {
                    sessionToken = data.token;
                    localStorage.setItem('sessionToken', sessionToken);
                    document.getElementById('shortLink').href = data.url;
                    document.getElementById('linkDisplay').classList.add('show');
                    showMessage('✅ Link sẵn sàng! Hãy vượt link và đợi 15 giây.', 'success');
                    startCountdown(15);
                    document.getElementById('linkDisplay').scrollIntoView({ behavior: 'smooth', block: 'center' });
                } else {
                    showMessage('❌ ' + data.msg, 'error');
                    document.getElementById('getLinkBtn').disabled = false;
                }
            } catch (error) {
                showMessage('❌ Lỗi: ' + error.message, 'error');
                document.getElementById('getLinkBtn').disabled = false;
            } finally {
                showLoading(false);
            }
        }
        async function getKey() {
            if (!sessionToken) { showMessage('❌ Vui lòng lấy link trước!', 'error'); return; }
            showLoading(true);
            document.getElementById('getKeyBtn').disabled = true;
            try {
                const response = await fetch(`/api/get_key?token=${sessionToken}`);
                const data = await response.json();
                if (data.status === 'ok') {
                    document.getElementById('keyValue').textContent = data.key;
                    document.getElementById('keyExpire').textContent = 'Hết hạn: ' + data.expire_at;
                    document.getElementById('keyDisplay').classList.add('show');
                    showMessage('🎉 Lấy key thành công!', 'success');
                    try {
                        navigator.clipboard.writeText(data.key);
                        setTimeout(() => showMessage('📋 Key đã copy!', 'info'), 1000);
                    } catch (e) {}
                    document.getElementById('keyDisplay').scrollIntoView({ behavior: 'smooth', block: 'center' });
                } else {
                    showMessage('❌ ' + data.msg, 'error');
                    document.getElementById('getKeyBtn').disabled = false;
                }
            } catch (error) {
                showMessage('❌ Lỗi: ' + error.message, 'error');
                document.getElementById('getKeyBtn').disabled = false;
            } finally {
                showLoading(false);
            }
        }
        if (sessionToken) {
            document.getElementById('getKeyBtn').disabled = false;
            showMessage('💡 Nếu đủ 15 giây, hãy nhấn "Lấy Key"', 'info');
        }
    </script>
</body>
</html>'''

@app.route("/api/get_link")
def get_link():
    """Tạo link Link4m"""
    if not LINK4M_KEY:
        return jsonify({"status": "error", "msg": "Chưa cấu hình LINK4M_KEY"})
    
    session_token = generate_session_token()
    unique_key = generate_key()
    
    # ✅ SỬA: URL đích không quan trọng vì chỉ cần user vượt link
    destination_url = "https://areskey.vercel.app"
    
    try:
        # ✅ SỬA: Đúng endpoint /st
        link4m_url = f"https://link4m.co/st?api={LINK4M_KEY}&url={destination_url}"
        resp = requests.get(link4m_url, timeout=10)
        short_url = resp.text.strip()
        
        if not short_url.startswith('http'):
            return jsonify({"status": "error", "msg": "Link4m API lỗi"})
        
        # Lưu session
        data = load_data()
        data["sessions"][session_token] = {
            "unique_key": unique_key,
            "created_at": time.time(),
            "link_clicked": False,
            "ip_address": request.remote_addr
        }
        save_data(data)
        
        return jsonify({
            "status": "ok",
            "message": "Vượt link và đợi 15 giây",
            "url": short_url,
            "token": session_token
        })
    except Exception as e:
        return jsonify({"status": "error", "msg": f"Lỗi: {str(e)}"})

@app.route("/api/get_key")
def get_key():
    """Lấy key"""
    session_token = request.args.get("token")
    if not session_token:
        return jsonify({"status": "error", "msg": "Thiếu token"})
    
    data = load_data()
    if session_token not in data.get("sessions", {}):
        return jsonify({"status": "error", "msg": "Session không tồn tại"})
    
    session = data["sessions"][session_token]
    created_at = session.get("created_at", 0)
    current_time = time.time()
    
    # Kiểm tra hết hạn
    if current_time - created_at > 86400:
        del data["sessions"][session_token]
        save_data(data)
        return jsonify({"status": "error", "msg": "Session đã hết hạn"})
    
    # Kiểm tra 15 giây
    time_elapsed = current_time - created_at
    if time_elapsed < 15:
        remaining = int(15 - time_elapsed)
        return jsonify({"status": "error", "msg": f"Đợi thêm {remaining} giây"})
    
    unique_key = session.get("unique_key")
    expire_time = created_at + 86400
    
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
    """Kiểm tra key"""
    key = request.args.get("key")
    if not key:
        return jsonify({"status": "fail", "msg": "Thiếu key"})
    
    data = load_data()
    current_time = time.time()
    
    for session_token, session_data in data.get("sessions", {}).items():
        if session_data.get("unique_key") == key:
            created_at = session_data.get("created_at", 0)
            if current_time - created_at > 86400:
                del data["sessions"][session_token]
                save_data(data)
                return jsonify({"status": "fail", "msg": "Key đã hết hạn"})
            
            expire_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(created_at + 86400))
            return jsonify({"status": "ok", "msg": "Key hợp lệ", "expire_at": expire_at, "is_unique": True})
    
    return jsonify({"status": "fail", "msg": "Key không tồn tại"})

if __name__ == "__main__":
    app.run(debug=True)
