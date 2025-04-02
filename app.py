from flask import Flask, render_template, request, send_file, url_for, jsonify, send_from_directory
from io import BytesIO
import qrcode
import os
import re
import base64
import logging
from barcode import Code128
from barcode.writer import SVGWriter
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

def create_barcode(number):
    try:
        logger.debug(f"Creating barcode for number: {number}")
        
        def code128_pattern(data):
            patterns = {
                '0': '11011001100', '1': '11001101100', '2': '11001100110',
                '3': '10010011000', '4': '10010001100', '5': '10000101100',
                '6': '10000100110', '7': '11001001000', '8': '11001000100',
                '9': '10100011100'
            }
            return ''.join(patterns.get(d, '') for d in data)
        
        # 바코드 패턴 생성
        pattern = code128_pattern(str(number))
        
        # 이미지 크기 설정
        bar_width = 3  # 바코드 선 두께
        width = len(pattern) * bar_width
        height = 100
        
        # 흰색 배경의 이미지 생성
        image = Image.new('RGB', (width + 40, height + 40), 'white')  # 여백 추가
        draw = ImageDraw.Draw(image)
        
        # 바코드 그리기
        for i, bit in enumerate(pattern):
            if bit == '1':
                x = i * bar_width + 20  # 여백 20px
                draw.rectangle([x, 20, x + bar_width - 1, height + 20], fill='black')
        
        # 이미지를 바이트로 변환
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)
        
        logger.debug("Barcode created successfully")
        return buffer
            
    except Exception as e:
        logger.error(f"Barcode creation error for {number}: {str(e)}")
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