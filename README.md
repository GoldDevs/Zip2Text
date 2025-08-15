# Zip2Text Real-time OCR (PHP Version)

This project is a PHP port of the original Zip2Text Python application. It is a secure, modern web application that extracts text from images contained within a ZIP file, providing a live, step-by-step log of the entire OCR process using Server-Sent Events (SSE).

The project is structured as a standard Composer package, making its components potentially reusable.

## Key Features

- **Real-time Progress Logging:** Watch every step of the process (validation, extraction, image scanning, OCR) as it happens using SSE.
- **ZIP File Support:** Upload a single `.zip` file containing multiple images.
- **Drag & Drop Interface:** Modern, easy-to-use interface for uploading files.
- **Google Cloud Vision OCR:** Utilizes Google's powerful Vision API for high-quality text extraction.
- **Asynchronous Job Queue:** The backend processing is handled by a background worker, ensuring the UI remains responsive and can handle long-running tasks.
- **Secure by Design:** Follows security best practices, such as validating uploads, using secure file paths, and preventing directory traversal.

## Architecture Overview

The application uses a client-server architecture built with vanilla PHP and JavaScript.

- **Frontend:** A single-page vanilla JavaScript application that communicates with the backend via:
    - **HTTP (`fetch`):** For uploading the initial ZIP file.
    - **Server-Sent Events (`EventSource`):** For receiving a one-way stream of log events from the server in real-time.
- **Backend:** The backend is composed of two main parts:
    1.  **Public Endpoints:** Simple PHP scripts in the `public/` directory (`upload.php`, `events.php`) that handle web requests.
    2.  **Background Worker:** A long-running command-line script (`worker.php`) that polls a file-based job queue.
- **Asynchronous Processing:** When a file is uploaded, `upload.php` creates a "job file" in the `jobs/` directory. The `worker.php` script picks up this job and executes the pipeline, ensuring that long-running OCR tasks do not block web requests.
- **OCR Pipeline (`src/`):** The processing pipeline is a series of PHP classes executed by the `JobManager`:
    - `ZipHandler`: Validates and extracts the uploaded ZIP file.
    - `ImageProcessor`: Scans the extracted files for supported image types.
    - `VisionClient`: Sends the images to the Google Cloud Vision API.
    - `TextAggregator`: Collects the OCR results into a final text document.
    - `EventLogger`: Writes structured logs that are streamed by the `events.php` endpoint.

## Prerequisites

- PHP 8.0+ with the following extensions: `zip`, `curl`, `gd`, `mbstring`, `intl`.
- Composer for dependency management.
- A Google Cloud Platform (GCP) project with the **Cloud Vision API** enabled.
- Billing enabled for your GCP project.

## Setup & Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Install dependencies:**
    ```bash
    composer install
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

    **Note:** Do not commit your credentials file to version control. The `.gitignore` file is already configured to ignore application data directories (`uploads`, `jobs`, `logs`).

## How to Run

Running this application requires two components: a web server to serve the frontend and a background worker to process the jobs.

### 1. Run the Background Worker

Open a terminal and run the following command from the project root. This script will run continuously, waiting for new jobs to process.

```bash
php worker.php
```
In a production environment, you should use a process manager like `supervisor` or `systemd` to keep this worker running permanently.

### 2. Run the Web Server

You need to serve the `public/` directory with a web server. The easiest way to do this for local development is to use PHP's built-in web server.

Open a **second terminal** and run this command from the project root:

```bash
php -S localhost:8000 -t public
```

The application will be available at `http://localhost:8000`. You will need to create a `public/index.php` file to serve the `templates/index.html` file.

## How to Use

1.  Open your web browser and navigate to `http://localhost:8000`.
2.  Drag and drop a `.zip` file containing your images onto the upload area, or use the "Select File" button.
3.  The upload will start automatically. Once uploaded, the live log panel will appear.
4.  Watch as the application validates, extracts, and processes each image.
5.  When the process is complete, the final extracted text will appear in the results card.
