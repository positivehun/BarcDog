from flask import Flask, render_template, request, send_file, url_for
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
import qrcode
import os

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.form.get('data')
        code_type = request.form.get('code_type')
        
        if not data:
            return "데이터를 입력해주세요.", 400
        
        if code_type == 'barcode':
            # 바코드 생성
            code128 = barcode.get('code128', data, writer=ImageWriter())
            buffer = BytesIO()
            code128.write(buffer)
            buffer.seek(0)
            return send_file(buffer, mimetype='image/png')
        else:
            # QR 코드 생성
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            return send_file(buffer, mimetype='image/png')
    except Exception as e:
        return str(e), 500

# Vercel 서버리스 함수
def handler(request):
    with app.request_context(request):
        return app.dispatch_request()

if __name__ == '__main__':
    app.run(debug=True) 