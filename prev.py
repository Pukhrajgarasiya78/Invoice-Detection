import base64
from flask import Flask, render_template, request, jsonify
import cv2
import easyocr
import numpy as np
import requests
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
            image = np.array(bytearray(response.content), dtype=np.uint8)
            image = cv2.imdecode(image, cv2.IMREAD_COLOR)
            return image
        else:
            print(f"Error: Unable to fetch the image. Status code: {response.status_code}")
    except Exception as e:
        print(f"Exception occurred: {e}")
    return None

# Function to preprocess the image
def preprocess_image(image):
    zoom_factor = 1.0  # Set your desired zoom factor here

    if len(image.shape) == 2:  # Check if the image is grayscale
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

    height, width = image.shape[:2]
    center_x, center_y = width // 2, height // 2

    new_width, new_height = int(width * zoom_factor), int(height * zoom_factor)
    left_x = max(center_x - new_width // 2, 0)
    right_x = min(center_x + new_width // 2, width)
    top_y = max(center_y - new_height // 2, 0)
    bottom_y = min(center_y + new_height // 2, height)

    cropped_image = image[top_y:bottom_y, left_x:right_x]
    zoomed_image = cv2.resize(cropped_image, (width, height))

    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharpened = cv2.filter2D(zoomed_image, -1, kernel)

    contrast_adjusted = adjust_contrast(sharpened)

    return contrast_adjusted

# Function to adjust contrast
def adjust_contrast(image):
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2Lab)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    limg = cv2.merge((cl, a, b))
    return cv2.cvtColor(limg, cv2.COLOR_Lab2BGR)

# Function to check orientation (this is more relevant for pytesseract)
def check_orientation(image):
    # EasyOCR does not provide orientation information in the same way as pytesseract
    # If needed, you may handle rotation separately based on your use case
    return 0  # Assume no rotation needed

# Function to rotate image
def rotate_image(image, angle):
    (h, w) = image.shape[:2]
    (cX, cY) = (w // 2, h // 2)
    new_w = int(h * abs(np.sin(np.radians(angle))) + w * abs(np.cos(np.radians(angle))))
    new_h = int(w * abs(np.sin(np.radians(angle))) + h * abs(np.cos(np.radians(angle))))
    M = cv2.getRotationMatrix2D((cX, cY), angle, 1.0)
    M[0, 2] += (new_w / 2) - cX
    M[1, 2] += (new_h / 2) - cY
    return cv2.warpAffine(image, M, (new_w, new_h))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process-image', methods=['POST'])
def process_image():
    if 'image_file' in request.files:
        # Process the uploaded image file
        image_file = request.files['image_file']
        img = np.frombuffer(image_file.read(), np.uint8)
        img = cv2.imdecode(img, cv2.IMREAD_COLOR)
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
        _, buffer = cv2.imencode('.jpg', preprocessed_img)
        img_str = base64.b64encode(buffer).decode('utf-8')

        results = reader.readtext(preprocessed_img)
        text_block = ' '.join([text for _, text, _ in results])

        json_data = json.dumps(text_block)
        save_to_database(json_data)

        return jsonify({"extracted_text": text_block, "image": img_str})
    else:
        return jsonify({"error": "Failed to process the image."}), 400

if __name__ == '__main__':
    app.run(debug=True)
