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
import zipfile
from datetime import datetime

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
            return render_template('error.html', error_message="데이터를 입력해주세요.")
        
        # QR 코드와 바코드의 유효성 검사를 분리
        if code_type == 'barcode':
            # 바코드는 숫자, 영문자, 특수문자(_, -) 허용
            if not all(re.match(r'^[0-9A-Za-z_\- ]+$', line.strip()) for line in data.splitlines() if line.strip()):
                return render_template('error.html', error_message="올바르지 않은 데이터입니다. 바코드는 숫자, 영문자, 특수문자(_, -) 만 입력 가능합니다.")
        
        # 쉼표, 공백, 줄바꿈으로 구분된 여러 데이터 처리
        parsed_data = []
        for line in data.splitlines():
            # 각 줄에서 쉼표나 공백으로 구분된 항목 처리
            items = [item.strip() for item in re.split(r'[,\s]+', line.strip()) if item.strip()]
            parsed_data.extend(items)
        
        if len(parsed_data) == 0:
            return render_template('error.html', error_message="유효한 데이터를 입력해주세요.")
        
        logger.debug(f"Parsed data: {parsed_data}")
        
        codes = []
        for item in parsed_data:
            try:
                if code_type == 'barcode':
                    buffer = create_barcode(item)
                else:  # qrcode
                    buffer = create_qrcode(item)
                    
                if buffer and buffer.getvalue():
                    codes.append({
                        'number': item,
                        'code': buffer.getvalue(),
                        'type': code_type
                    })
                    logger.debug(f"Successfully created code for data: {item}")
                else:
                    logger.error(f"Failed to create code for data: {item}")
                    return render_template('error.html', error_message="코드 생성에 실패했습니다.")
            except Exception as e:
                logger.error(f"Error creating code for data {item}: {str(e)}")
                return render_template('error.html', error_message="코드 생성 중 오류가 발생했습니다.")
        
        if not codes:
            return render_template('error.html', error_message="코드 생성에 실패했습니다. 입력된 데이터를 확인해주세요.")
            
        return render_template('result.html', codes=codes)
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return render_template('error.html', error_message="처리 중 오류가 발생했습니다. 다시 시도해주세요.")

@app.route('/download_codes', methods=['POST'])
def download_codes():
    try:
        # ZIP 파일 생성
        memory_file = BytesIO()
        with zipfile.ZipFile(memory_file, 'w') as zf:
            codes_data = request.get_json()
            for idx, code in enumerate(codes_data, 1):
                # Base64 디코딩
                code_data = base64.b64decode(code['code'])
                # 파일 이름 생성 (바코드/QR 코드 구분)
                file_ext = 'png' if code['type'] == 'qrcode' else 'png'  # 둘 다 PNG로 저장
                filename = f"{code['type']}_{code['number']}_{idx}.{file_ext}"
                zf.writestr(filename, code_data)
        
        memory_file.seek(0)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'barcdog_codes_{timestamp}.zip'
        )
    except Exception as e:
        logger.error(f"Error creating zip file: {str(e)}")
        return jsonify({"error": "파일 생성 중 오류가 발생했습니다."}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 