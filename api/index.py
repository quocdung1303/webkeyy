from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    """Trang chủ - Chuyển hướng về hướng dẫn"""
    try:
        with open('folder/huongdan.html', 'r', encoding='utf-8') as f:
            return f.read()
    except:
        return """
        <!DOCTYPE html>
        <html lang="vi">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>ARES Tool - Hướng dẫn</title>
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 20px;
                }
                .container {
                    max-width: 900px;
                    width: 100%;
                    background: rgba(255, 255, 255, 0.95);
                    border-radius: 20px;
                    padding: 50px;
                    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                }
                .logo {
                    text-align: center;
                    font-size: 56px;
                    font-weight: 900;
                    background: linear-gradient(135deg, #667eea, #764ba2);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    margin-bottom: 20px;
                    font-family: 'Courier New', monospace;
                }
                h1 {
                    text-align: center;
                    color: #333;
                    font-size: 32px;
                    margin-bottom: 30px;
                }
                .content {
                    color: #555;
                    font-size: 18px;
                    line-height: 1.8;
                }
                .section {
                    margin-bottom: 30px;
                    padding: 20px;
                    background: rgba(102, 126, 234, 0.05);
                    border-radius: 10px;
                    border-left: 4px solid #667eea;
                }
                .section h2 {
                    color: #667eea;
                    font-size: 24px;
                    margin-bottom: 15px;
                }
                .section p {
                    margin-bottom: 10px;
                }
                .footer {
                    text-align: center;
                    margin-top: 40px;
                    padding-top: 20px;
                    border-top: 2px solid rgba(102, 126, 234, 0.2);
                    color: #999;
                    font-size: 14px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="logo">ARES</div>
                <h1>📖 Hướng dẫn sử dụng ARES Tool</h1>
                
                <div class="content">
                    <div class="section">
                        <h2>🎯 Giới thiệu</h2>
                        <p>ARES Tool là công cụ hỗ trợ người dùng tạo và quản lý key miễn phí với hệ thống bảo mật đa lớp.</p>
                    </div>
                    
                    <div class="section">
                        <h2>⚙️ Tính năng chính</h2>
                        <p>✅ Tạo key ngẫu nhiên an toàn</p>
                        <p>✅ Giới hạn 3 IP mỗi key</p>
                        <p>✅ Thời gian sử dụng: 24 giờ</p>
                        <p>✅ Hệ thống antibot bảo vệ</p>
                    </div>
                    
                    <div class="section">
                        <h2>📝 Hướng dẫn sử dụng</h2>
                        <p><strong>Bước 1:</strong> Click nút "Bắt đầu lấy key"</p>
                        <p><strong>Bước 2:</strong> Vượt link xác minh</p>
                        <p><strong>Bước 3:</strong> Đợi 80 giây</p>
                        <p><strong>Bước 4:</strong> Nhận key và sử dụng</p>
                    </div>
                    
                    <div class="section">
                        <h2>⚠️ Lưu ý quan trọng</h2>
                        <p>• Mỗi key chỉ sử dụng được trên tối đa 3 thiết bị</p>
                        <p>• Key hết hạn sau 24 giờ kể từ khi tạo</p>
                        <p>• Không chia sẻ key cho người khác để tránh vượt giới hạn IP</p>
                    </div>
                </div>
                
                <div class="footer">
                    <p>© 2025 ARES Tool - Phiên bản V27</p>
                    <p>Mọi thắc mắc vui lòng liên hệ qua Telegram</p>
                </div>
            </div>
        </body>
        </html>
        """

@app.route("/huong-dan")
def huong_dan():
    """Trang hướng dẫn (route phụ)"""
    return home()
