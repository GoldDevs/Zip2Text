# Zip2Text Real-time OCR Web App

Zip2Text is a highly interactive web application that extracts text from images contained within a ZIP file. It provides a live, step-by-step log of the entire OCR process, from file upload to the final text aggregation, using real-time events.

## Key Features

- **Real-time Progress Logging:** Watch every step of the process (validation, extraction, image scanning, OCR) as it happens.
- **ZIP File Support:** Upload a single `.zip` file containing multiple images.
- **Drag & Drop Interface:** Modern, easy-to-use interface for uploading files.
- **Google Cloud Vision OCR:** Utilizes Google's powerful Vision API for high-quality text extraction.
- **Asynchronous Pipeline:** The backend processing is fully asynchronous, ensuring the UI remains responsive.
- **Mobile Responsive:** The interface is designed to be usable on both desktop and mobile devices.

## Architecture Overview

The application uses a client-server architecture built with Python, Flask, and Flask-SocketIO.

- **Backend:** The Flask application serves the main web page and handles the initial file upload. Upon receiving a file, it spawns a background task to handle the processing pipeline.
- **Real-time Communication:** [Flask-SocketIO](https://flask-socketio.readthedocs.io/) is used with an `eventlet` worker to stream log events from the server to the client in real-time. Each job is assigned a unique room to ensure clients only see their own logs.
- **OCR Pipeline:** The processing pipeline is a series of modules that are executed in order:
    1.  `zip_handler`: Validates and extracts the uploaded ZIP file.
    2.  `image_processor`: Scans the extracted files for supported image types.
    3.  `vision_client`: Sends the images to the Google Cloud Vision API.
    4.  `text_aggregator`: Collects the OCR results into a final text document.
- **Frontend:** A vanilla JavaScript single-page application that communicates with the backend via HTTP (for uploads) and WebSockets (for real-time logs). It dynamically updates the DOM to show the live log and final results.

## Prerequisites

- Python 3.9+
- A Google Cloud Platform (GCP) project with the **Cloud Vision API** enabled.
- Billing enabled for your GCP project.

## Setup & Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    # On Windows, use: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    The application's dependencies are listed in `zip2text_app/requirements.txt`.
    ```bash
    pip install -r zip2text_app/requirements.txt
    ```

## Configuration

This application requires Google Cloud credentials to use the Vision API.

1.  **Create a Service Account:**
    - In the Google Cloud Console, navigate to "IAM & Admin" > "Service Accounts".
    - Create a new service account. Grant it the "Cloud Vision AI User" role.
    - After creating the service account, go to its "Keys" tab, click "Add Key", and create a new JSON key. A JSON file will be downloaded to your computer.

2.  **Set the Environment Variable:**
    The application loads the credentials from an environment variable named `GOOGLE_APPLICATION_CREDENTIALS_JSON`. You must set this variable to the *content* of the JSON key file you downloaded.

    **Linux/macOS:**
    ```bash
    export GOOGLE_APPLICATION_CREDENTIALS_JSON='<paste-the-entire-content-of-your-json-file-here>'
    ```

    **Windows (PowerShell):**
    ```powershell
    $env:GOOGLE_APPLICATION_CREDENTIALS_JSON='<paste-the-entire-content-of-your-json-file-here>'
    ```

    **Note:** Do not commit your credentials file to version control.

## How to Run

### Development Mode

For local development, you can run the Flask-SocketIO development server directly. This provides live reloading and debugging information.

```bash
python zip2text_app/app.py
```

The application will be available at `http://127.0.0.1:5001`.

### Production Mode

For production, it is recommended to use the `gunicorn` WSGI server, as configured in the `Procfile`.

```bash
gunicorn --worker-class eventlet -w 1 --log-level info zip2text_app.app:app
```

This will start the server on the default port (usually 8000).

## How to Use

1.  Open your web browser and navigate to the application's URL.
2.  Drag and drop a `.zip` file containing your images onto the upload area, or use the "Select File" button.
3.  The upload will start automatically. Once uploaded, the live log panel will appear.
4.  Watch as the application validates, extracts, and processes each image.
5.  When the process is complete, the final extracted text will appear in the results card. You can then copy the text or download it as a `.txt` file.

## Running Tests

The project includes a suite of unit tests for the backend pipeline. To run the tests:

```bash
python zip2text_app/tests/test_pipeline.py
```
