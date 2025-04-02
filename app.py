from flask import Flask, render_template, request, send_file, url_for, jsonify, send_from_directory
from io import BytesIO
import qrcode
import os
import re
import base64
import logging
from barcode import Code128
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw

# 로깅 설정
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.template_filter('b64encode')
def b64encode_filter(data):
    return base64.b64encode(data).decode()

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                             'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/')
def home():
    return render_template('index.html')

def parse_numbers(input_string):
    # 여러 가지 구분자로 분리 (쉼표, 공백, 쉼표+공백)
    numbers = re.split(r'[,\s]+', input_string.strip())
    # 빈 문자열 제거
    return [num.strip() for num in numbers if num.strip()]

def create_barcode(data):
    try:
        logger.debug(f"Creating barcode for data: {data}")
        
        # Code128 바코드 생성 (Auto 모드)
        rv = BytesIO()
        # Code128 Auto 모드로 생성 (문자, 숫자 자동 최적화)
        Code128(str(data), writer=ImageWriter()).write(rv, {
            'module_width': 0.4,     # 바코드 선 두께
            'module_height': 15.0,   # 바코드 높이
            'quiet_zone': 6.0,       # 여백
            'font_size': 10,         # 텍스트 크기
            'text_distance': 5.0,    # 텍스트와 바코드 사이 거리
            'background': 'white',   # 배경색
            'foreground': 'black',   # 바코드 색
            'write_text': True,      # 바코드 아래 텍스트 표시
            'dpi': 300,             # 해상도
        })
        
        rv.seek(0)
        logger.debug("Barcode created successfully")
        return rv
            
    except Exception as e:
        logger.error(f"Barcode creation error for {data}: {str(e)}")
        raise

def create_qrcode(number):
    try:
        logger.debug(f"Creating QR code for number: {number}")
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(str(number))
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, "PNG")
        buffer.seek(0)
        logger.debug("QR code created successfully")
        return buffer
    except Exception as e:
        logger.error(f"QR code creation error for {number}: {str(e)}")
        raise

@app.route('/generate', methods=['GET', 'POST'])
def generate():
    if request.method == 'GET':
        return render_template('index.html')
        
    try:
        data = request.form.get('data')
        code_type = request.form.get('code_type')
        
        logger.debug(f"Received request - Data: {data}, Type: {code_type}")
        
        if not data:
            return jsonify({"error": "데이터를 입력해주세요."}), 400
        
        parsed_numbers = parse_numbers(data)
        if len(parsed_numbers) == 0:
            return jsonify({"error": "유효한 숫자를 입력해주세요."}), 400
        
        logger.debug(f"Parsed numbers: {parsed_numbers}")
        
        # 각 숫자에 대한 코드 생성
        codes = []
        for number in parsed_numbers:
            try:
                if code_type == 'barcode':
                    buffer = create_barcode(number)
                else:  # qrcode
                    buffer = create_qrcode(number)
                    
                if buffer and buffer.getvalue():
                    codes.append({
                        'number': number,
                        'code': buffer.getvalue(),
                        'type': code_type
                    })
                    logger.debug(f"Successfully created code for number: {number}")
                else:
                    logger.error(f"Failed to create code for number: {number}")
            except Exception as e:
                logger.error(f"Error creating code for number {number}: {str(e)}")
                continue
        
        if not codes:
            return jsonify({"error": "코드 생성 중 오류가 발생했습니다. 입력된 데이터를 확인해주세요."}), 500
            
        return render_template('result.html', codes=codes)
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 