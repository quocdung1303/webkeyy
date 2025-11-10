from flask import Flask, request, jsonify
import json
import os
import time
import random
import string
import secrets

app = Flask(__name__)

LINK4M_KEY = os.getenv("LINK4M_KEY", "6906d12068643654b40df4e9")

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
    try:
        with open(KEY_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except:
        pass

def cleanup_old_sessions():
    """Xóa session cũ hơn 24 giờ"""
    try:
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
    except:
        pass

@app.before_request
def auto_cleanup():
    """Tự động cleanup trước mỗi request"""
    try:
        cleanup_old_sessions()
    except:
        pass

@app.route("/")
def home():
    """Trang chủ"""
    try:
        with open('folder/index.html', 'r', encoding='utf-8') as f:
            return f.read()
    except:
        return "ARES Tool - index.html not found"

@app.route("/huong-dan")
def huong_dan():
    """Trang hướng dẫn"""
    try:
        with open('folder/huongdan.html', 'r', encoding='utf-8') as f:
            return f.read()
    except:
        return "Hướng dẫn - huongdan.html not found"

@app.route("/api/get_link")
def get_link():
    """Tạo link Link4m trực tiếp"""
    try:
        session_token = generate_session_token()
        unique_key = generate_key()
        
        # URL đích
        destination_url = "https://areskey.vercel.app"
        
        # Link Link4m trực tiếp
        link4m_url = f"https://link4m.co/st?api={LINK4M_KEY}&url={destination_url}"
        
        # Lưu session
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
            "url": link4m_url,
            "token": session_token
        })
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

@app.route("/api/get_key")
def get_key():
    """Lấy KEY sau khi đã đợi đủ thời gian"""
    try:
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
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

@app.route("/api/check_key")
def check_key():
    """Kiểm tra key có hợp lệ không - Tối đa 3 IP"""
    try:
        key = request.args.get("key")
        
        if not key:
            return jsonify({"status": "fail", "msg": "Thiếu key"})
        
        data = load_data()
        current_time = time.time()
        current_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if current_ip:
            current_ip = current_ip.split(',')[0].strip()
        else:
            current_ip = request.remote_addr
        
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
    except Exception as e:
        return jsonify({"status": "fail", "msg": str(e)})
