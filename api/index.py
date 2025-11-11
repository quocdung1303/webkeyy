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
                    font-family: 'Segoe UI', sans-serif;
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
                    <p>Trang hướng dẫn đang được cập nhật...</p>
                </div>
                <div class="footer">
                    <p>© 2025 ARES Tool V27</p>
                </div>
            </div>
        </body>
        </html>
        """

@app.route("/huong-dan")
def huong_dan():
    """Trang hướng dẫn (route phụ)"""
    return home()
