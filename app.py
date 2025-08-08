import os
import zipfile
import tempfile
import logging
import json
import re
from pathlib import Path

from flask import Flask, request, render_template_string
from google.cloud import vision
from google.oauth2 import service_account

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}

# Initialize Flask App
app = Flask(__name__)

# --- Helper Functions ---

def natural_sort_key(s: str) -> list:
    """Sorts strings with numbers in a natural way (e.g., page2 before page10)."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

def initialize_vision_client():
    """Initializes the Vision API client safely from environment variables."""
    credentials_json_str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if not credentials_json_str:
        logging.critical("CRITICAL: GOOGLE_APPLICATION_CREDENTIALS_JSON environment variable is not set.")
        raise EnvironmentError("Google Cloud credentials not found in environment.")
    
    try:
        credentials_info = json.loads(credentials_json_str)
        credentials = service_account.Credentials.from_service_account_info(credentials_info)
        client = vision.ImageAnnotatorClient(credentials=credentials)
        logging.info("Google Cloud Vision client initialized successfully.")
        return client
    except Exception as e:
        logging.critical(f"Failed to initialize Google Vision client: {e}")
        raise

def extract_text_from_image(client: vision.ImageAnnotatorClient, image_path: Path) -> str:
    """Uses Google Cloud Vision API to perform OCR on a single image."""
    try:
        with open(image_path, "rb") as image_file:
            content = image_file.read()
        image = vision.Image(content=content)
        response = client.document_text_detection(image=image)
        if response.error.message:
            raise Exception(response.error.message)
        return response.full_text_annotation.text
    except Exception as e:
        logging.error(f"Could not process image {image_path.name} with Vision API: {e}")
        return f"[Error processing {image_path.name}: {e}]"

# --- Web App Routes ---

@app.route('/', methods=['GET'])
def index():
    """Renders the main upload page."""
    # This is an HTML page defined directly in Python for simplicity.
    return render_template_string('''
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Comic OCR Uploader</title>
        <style>
          body { font-family: sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; line-height: 1.6; background-color: #f4f4f4; }
          h1 { color: #333; }
          .container { background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
          input[type=file] { margin-bottom: 10px; }
          input[type=submit] { background: #007bff; color: white; padding: 10px 15px; border: none; border-radius: 4px; cursor: pointer; }
          .loader { display: none; border: 8px solid #f3f3f3; border-radius: 50%; border-top: 8px solid #3498db; width: 50px; height: 50px; animation: spin 2s linear infinite; margin: 20px auto; }
          @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        </style>
      </head>
      <body>
        <div class="container">
          <h1>Upload Your Comic .zip File</h1>
          <form method="post" enctype="multipart/form-data" onsubmit="document.getElementById('loader').style.display = 'block';">
            <input type="file" name="file" accept=".zip" required>
            <br>
            <input type="submit" value="Extract Text">
          </form>
          <div id="loader" class="loader"></div>
        </div>
      </body>
    </html>
    ''')

@app.route('/', methods=['POST'])
def upload_and_process():
    """Handles the file upload and OCR processing."""
    if 'file' not in request.files:
        return "No file part", 400
    file = request.files['file']
    if file.filename == '' or not file.filename.endswith('.zip'):
        return "No selected file or file is not a zip", 400

    try:
        client = initialize_vision_client()
    except Exception as e:
        return f"<h1>Error</h1><p>Could not initialize OCR service. Check server configuration.</p><pre>{e}</pre>", 500
    
    final_text = f"<h1>OCR Results for {file.filename}</h1>\n<pre>"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        zip_path = tmp_path / file.filename
        file.save(zip_path)

        logging.info(f"Extracting '{zip_path.name}'...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(tmp_path)
        
        image_files = sorted(
            [p for p in tmp_path.glob('**/*') if p.suffix.lower() in SUPPORTED_EXTENSIONS],
            key=lambda x: natural_sort_key(x.name)
        )

        if not image_files:
            return "<h1>Error</h1><p>No supported image files (.jpg, .png, etc.) found in the zip archive.</p>", 400
        
        for i, image_path in enumerate(image_files):
            logging.info(f"Processing page {i+1}/{len(image_files)}: {image_path.name}")
            final_text += f"\n--- Page {i+1}: {image_path.name} ---\n\n"
            text = extract_text_from_image(client, image_path)
            final_text += text.replace('<', '&lt;').replace('>', '&gt;') # Basic HTML escaping
            final_text += "\n\n"

    final_text += "</pre>"
    return final_text

if __name__ == "__main__":
    # Kinsta will use a production server like Gunicorn, not this.
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
