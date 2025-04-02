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

def create_barcode(data):
    try:
        logger.debug(f"Creating barcode for data: {data}")
        
        def code128_pattern(data):
            # Code 128B 패턴 (ASCII 32-127)
            patterns = {
                # 숫자
                '0': '11011001100', '1': '11001101100', '2': '11001100110',
                '3': '10010011000', '4': '10010001100', '5': '10000101100',
                '6': '10000100110', '7': '11001001000', '8': '11001000100',
                '9': '10100011000',
                # 알파벳 대문자
                'A': '10100001100', 'B': '10010001100', 'C': '10001001100',
                'D': '10100011000', 'E': '10010011000', 'F': '10001011000',
                'G': '10000101100', 'H': '10000100110', 'I': '10110001000',
                'J': '10110000100', 'K': '10011010000', 'L': '10011000100',
                'M': '10000110100', 'N': '10000110010', 'O': '11000010010',
                'P': '11001010000', 'Q': '11110111010', 'R': '11000010100',
                'S': '10110111000', 'T': '10110001110', 'U': '10001101110',
                'V': '10111011000', 'W': '10111000110', 'X': '10001110110',
                'Y': '11101110110', 'Z': '11010001110',
                # 특수문자
                '_': '10010100000', '-': '10101000000',
            }
            
            # 시작 코드 B (ASCII)
            result = '11010010000'
            
            # 데이터 인코딩
            for char in str(data):
                if char in patterns:
                    result += patterns[char]
                else:
                    # 지원하지 않는 문자는 공백으로 대체
                    result += patterns['0']
            
            # 체크섬 계산
            checksum = 104  # 시작 문자 B의 값
            for i, char in enumerate(str(data)):
                if char in patterns:
                    checksum += (i + 1) * (ord(char) - 32)
            checksum = checksum % 103
            
            # 체크섬 패턴 추가
            checksum_pattern = patterns.get(str(checksum % 10), patterns['0'])
            result += checksum_pattern
            
            # 정지 패턴
            result += '1100011101011'
            
            return result
        
        # 바코드 패턴 생성
        pattern = code128_pattern(str(data))
        
        # 이미지 크기 설정
        bar_width = 4  # 바코드 선 두께
        height = 150   # 바코드 높이 증가
        margin = 50    # 여백 증가
        
        # 전체 이미지 크기 계산
        width = len(pattern) * bar_width
        total_width = width + (margin * 2)
        total_height = height + (margin * 2)
        
        # 흰색 배경의 이미지 생성
        image = Image.new('RGB', (total_width, total_height), 'white')
        draw = ImageDraw.Draw(image)
        
        # 바코드 그리기
        for i, bit in enumerate(pattern):
            if bit == '1':
                x = (i * bar_width) + margin
                draw.rectangle([x, margin, x + bar_width - 1, height + margin], fill='black')
        
        # 이미지를 바이트로 변환
        buffer = BytesIO()
        image.save(buffer, format='PNG', dpi=(300, 300))  # DPI 증가
        buffer.seek(0)
        
        logger.debug("Barcode created successfully")
        return buffer
            
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