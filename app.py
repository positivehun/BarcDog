from flask import Flask, render_template, request, send_file, url_for, jsonify, send_from_directory
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
import qrcode
import os
import re
import base64
import logging

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
        # 바코드 생성
        code128 = barcode.get('code128', str(number))
        
        # 이미지 생성
        buffer = BytesIO()
        code128.save(buffer)
        buffer.seek(0)
        
        # 버퍼 내용 확인
        if buffer.getvalue():
            logger.debug("Barcode created successfully")
            return buffer
        else:
            logger.error("Empty buffer after barcode creation")
            raise Exception("바코드 생성 실패: 빈 이미지")
            
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