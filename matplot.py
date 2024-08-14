from flask import Flask, render_template, request, jsonify
import matplotlib.pyplot as plt
from PIL import Image, ImageEnhance, ImageOps
import easyocr
import numpy as np
import requests
import io
import base64
import json
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
            image = Image.open(io.BytesIO(response.content))
            return image
        else:
            print(f"Error: Unable to fetch the image. Status code: {response.status_code}")
    except Exception as e:
        print(f"Exception occurred: {e}")
    return None

# Function to preprocess the image
def preprocess_image(image):
    zoom_factor = 1.0  # Set your desired zoom factor here

    # Apply zoom
    width, height = image.size
    new_width, new_height = int(width * zoom_factor), int(height * zoom_factor)
    image = image.resize((new_width, new_height), Image.LANCZOS)
    
    # Center crop to original size
    left = (new_width - width) / 2
    top = (new_height - height) / 2
    right = (new_width + width) / 2
    bottom = (new_height + height) / 2
    image = image.crop((left, top, right, bottom))

    # Sharpening and contrast adjustment
    enhancer = ImageEnhance.Sharpness(image)
    image = enhancer.enhance(2.0)  # Increase sharpness

    image = adjust_contrast(image)

    return image

# Function to adjust contrast
def adjust_contrast(image):
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2.0)  # Increase contrast
    return image

# Function to rotate image (if necessary)
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
        img = Image.open(io.BytesIO(image_file.read()))
    elif request.form.get('image_url'):
        # Process the image URL
        image_url = request.form.get('image_url')
        img = download_image(image_url)
    else:
        return jsonify({"error": "No image data provided."}), 400

    if img is not None:
        # Preprocess image
        preprocessed_img = preprocess_image(img)
        
        # Convert to bytes for encoding
        buffered = io.BytesIO()
        preprocessed_img.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')

        # Extract text using EasyOCR
        results = reader.readtext(np.array(preprocessed_img))
        text_block = ' '.join([text for _, text, _ in results])

        json_data = json.dumps(text_block)
        save_to_database(json_data)

        return jsonify({"extracted_text": text_block, "image": img_str})
    else:
        return jsonify({"error": "Failed to process the image."}), 400

if __name__ == '__main__':
    app.run(debug=True)
