import base64
from flask import Flask, render_template, request, jsonify
from PIL import Image, ImageEnhance, ImageOps
import easyocr
import numpy as np
import requests
import json
from io import BytesIO  # Import BytesIO
from database import save_to_database  # Import the database function

app = Flask(__name__)
reader = easyocr.Reader(['en'])  # Initialize EasyOCR reader for English

# Function to download the image from URL
def download_image(url):
    try:
        headers = {
            'Accept': 'image/jpeg, image/png, image/*',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.114 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            image = Image.open(BytesIO(response.content))
            return image
        else:
            print(f"Error: Unable to fetch the image. Status code: {response.status_code}")
    except Exception as e:
        print(f"Exception occurred: {e}")
    return None

# Function to preprocess the image
def preprocess_image(image):
    zoom_factor = 1.0  # Set your desired zoom factor here

    if image.mode == 'L':  # Check if the image is grayscale
        image = image.convert('RGB')

    width, height = image.size
    new_width, new_height = int(width * zoom_factor), int(height * zoom_factor)
    left = (width - new_width) / 2
    top = (height - new_height) / 2
    right = (width + new_width) / 2
    bottom = (height + new_height) / 2

    image = image.crop((left, top, right, bottom))
    image = image.resize((width, height), Image.LANCZOS)

    enhancer = ImageEnhance.Sharpness(image)
    image = enhancer.enhance(2.0)  # Increase sharpness

    contrast = ImageEnhance.Contrast(image)
    image = contrast.enhance(2.0)  # Increase contrast

    return image

# Function to check orientation (this is more relevant for pytesseract)
def check_orientation(image):
    # EasyOCR does not provide orientation information in the same way as pytesseract
    # If needed, you may handle rotation separately based on your use case
    return 0  # Assume no rotation needed

# Function to rotate image
def rotate_image(image, angle):
    return image.rotate(angle, expand=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process-image', methods=['POST'])
def process_image():
    if 'image_file' in request.files:
        # Process the uploaded image file
        image_file = request.files['image_file']
        img = Image.open(image_file)
    elif request.form.get('image_url'):
        # Process the image URL
        image_url = request.form.get('image_url')
        img = download_image(image_url)
    else:
        return jsonify({"error": "No image data provided."}), 400

    if img is not None:
        # Check and rotate image if necessary
        rotation = check_orientation(img)
        if rotation != 0:
            img = rotate_image(img, -rotation)
        
        preprocessed_img = preprocess_image(img)
        buffered = BytesIO()
        preprocessed_img.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')

        results = reader.readtext(np.array(preprocessed_img))
        text_block = ' '.join([text for _, text, _ in results])

        json_data = json.dumps(text_block)
        save_to_database(json_data)

        return jsonify({"extracted_text": text_block, "image": img_str})
    else:
        return jsonify({"error": "Failed to process the image."}), 400

if __name__ == '__main__':
    app.run(debug=True)
