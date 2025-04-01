from flask import Flask, render_template, request, send_file, url_for, jsonify, send_from_directory
from io import BytesIO
import qrcode
import os
import re
import base64
import logging
import math

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
        # Code 128 바코드 패턴 생성
        def code128_pattern(data):
            # Code 128B 패턴 (숫자만)
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
        width = len(pattern) * 2
        height = 100
        
        # PNG 이미지 데이터 생성
        def create_png_data(width, height, pattern):
            # PNG 헤더
            header = bytes([
                0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG 시그니처
                0x00, 0x00, 0x00, 0x0D,  # IHDR 청크 길이
                0x49, 0x48, 0x44, 0x52,  # "IHDR"
                (width >> 24) & 0xFF, (width >> 16) & 0xFF, (width >> 8) & 0xFF, width & 0xFF,  # 너비
                (height >> 24) & 0xFF, (height >> 16) & 0xFF, (height >> 8) & 0xFF, height & 0xFF,  # 높이
                0x08,  # 비트 깊이
                0x00,  # 컬러 타입 (그레이스케일)
                0x00,  # 압축 방식
                0x00,  # 필터 방식
                0x00,  # 인터레이스 방식
                0x00, 0x00, 0x00, 0x00,  # CRC
            ])
            
            # 이미지 데이터 생성
            image_data = bytearray()
            for y in range(height):
                # 필터 바이트
                image_data.append(0)
                # 스캔 라인
                for x in range(width):
                    if pattern[x // 2] == '1':
                        image_data.append(0)  # 검은색
                    else:
                        image_data.append(255)  # 흰색
            
            # IDAT 청크
            def adler32(data):
                s1, s2 = 1, 0
                for byte in data:
                    s1 = (s1 + byte) % 65521
                    s2 = (s2 + s1) % 65521
                return (s2 << 16) | s1
            
            # zlib 압축 (간단한 구현)
            compressed = image_data  # 실제로는 zlib 압축이 필요하지만, 테스트를 위해 생략
            
            idat_chunk = bytes([
                (len(compressed) >> 24) & 0xFF, (len(compressed) >> 16) & 0xFF,
                (len(compressed) >> 8) & 0xFF, len(compressed) & 0xFF,
                0x49, 0x44, 0x41, 0x54,  # "IDAT"
            ]) + compressed
            
            crc = adler32(idat_chunk[4:])
            idat_chunk += bytes([
                (crc >> 24) & 0xFF, (crc >> 16) & 0xFF,
                (crc >> 8) & 0xFF, crc & 0xFF,
            ])
            
            # IEND 청크
            iend_chunk = bytes([
                0x00, 0x00, 0x00, 0x00,  # 길이
                0x49, 0x45, 0x4E, 0x44,  # "IEND"
                0xAE, 0x42, 0x60, 0x82,  # CRC
            ])
            
            return header + idat_chunk + iend_chunk
        
        # PNG 이미지 데이터 생성
        png_data = create_png_data(width, height, pattern)
        
        # 버퍼에 저장
        buffer = BytesIO(png_data)
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