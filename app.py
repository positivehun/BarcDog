from flask import Flask, render_template, request, send_file, jsonify
from barcode import Code128
from barcode.writer import ImageWriter
from io import BytesIO
import os
import re
import base64
import qrcode

app = Flask(__name__)

def parse_numbers(input_string):
    # 여러 가지 구분자로 분리 (쉼표, 공백, 쉼표+공백)
    numbers = re.split(r'[,\s]+', input_string.strip())
    # 빈 문자열 제거
    return [num.strip() for num in numbers if num.strip()]

def create_barcode(number):
    code128 = Code128(number, writer=ImageWriter())
    buffer = BytesIO()
    code128.write(buffer)
    buffer.seek(0)
    return buffer

def create_qrcode(number):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(number)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer

@app.template_filter('b64encode')
def b64encode_filter(data):
    return base64.b64encode(data).decode()

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        numbers = request.form['numbers']
        code_type = request.form.get('code_type', 'barcode')
        
        if numbers:
            parsed_numbers = parse_numbers(numbers)
            if len(parsed_numbers) == 0:
                return "유효한 숫자를 입력해주세요.", 400
            
            # 각 숫자에 대한 코드 생성
            codes = []
            for number in parsed_numbers:
                if code_type == 'barcode':
                    buffer = create_barcode(number)
                else:  # qrcode
                    buffer = create_qrcode(number)
                codes.append({
                    'number': number,
                    'code': buffer.getvalue(),
                    'type': code_type
                })
            
            return render_template('result.html', codes=codes)
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True) 