"""
Main Flask application for the Zip2Text service.

This file sets up the Flask server, configures Socket.IO for real-time communication,
and defines the routes for the web interface, including file uploads and event streaming.
It also manages the background task execution for the OCR pipeline.
"""

# Monkey-patch the standard library for eventlet
import eventlet
eventlet.monkey_patch()

import os
import uuid
import logging
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, join_room
from werkzeug.utils import secure_filename

# Import pipeline and real-time components
from .pipeline.job_manager import run_job
from .realtime.event_streamer import create_event_streamer

from logging.handlers import RotatingFileHandler

# --- App & SocketIO Initialization ---
app = Flask(__name__)

# Configure logging to a file
# This is more robust for a production-like environment
log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app.log')
log_handler = RotatingFileHandler(log_file, maxBytes=100000, backupCount=3)
log_handler.setLevel(logging.INFO)
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log_handler.setFormatter(log_formatter)

# Add the handler to Flask's logger and the root logger
app.logger.addHandler(log_handler)
logging.getLogger().addHandler(log_handler)
logging.getLogger().setLevel(logging.INFO)
# In a real app, use an environment variable for the secret key
app.config['SECRET_KEY'] = 'a_very_secret_key_that_should_be_more_secure'
# Define a folder for temporary uploads outside the app directory to avoid reloader conflicts
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Use eventlet as the async mode, consistent with the gunicorn worker.
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*")

# Create the event streamer instance. This will be passed to background jobs.
streamer = create_event_streamer(socketio)


# --- HTTP Routes ---
@app.route('/')
def index():
    """Serves the main HTML page."""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """
    Handles file uploads, saves the file, and starts the OCR pipeline.

    Expects a POST request with a 'file' part in the multipart/form-data.
    The file must be a .zip archive.

    On success, it starts a background task for processing and returns a JSON
    response with the unique job ID.
    On failure, it returns a JSON error message.

    Returns:
        Response: A JSON object containing either a 'job_id' or an 'error'.
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    if file and file.filename.endswith('.zip'):
        filename = secure_filename(file.filename)
        job_id = str(uuid.uuid4())
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{job_id}_{filename}")

        try:
            file.save(save_path)
            logging.info(f"File saved to {save_path}")

            # Start the OCR pipeline in a background thread, passing the streamer instance
            socketio.start_background_task(
                target=run_job_and_cleanup,
                job_id=job_id,
                zip_file_path=save_path,
                streamer=streamer
            )

            # Return the job_id to the client immediately
            return jsonify({"job_id": job_id})

        except Exception as e:
            logging.error(f"Error during file upload or job start: {e}")
            return jsonify({"error": "Failed to start processing."}), 500

    return jsonify({"error": "Invalid file type. Please upload a .zip file."}), 400

def run_job_and_cleanup(job_id: str, zip_file_path: str, streamer: "EventStreamer"):
    """
    A wrapper function to run the main OCR job and ensure cleanup.

    This function is designed to be executed in a background thread started
    by Socket.IO. It calls the main `run_job` from the pipeline and guarantees
    that the uploaded temporary file is deleted afterward, regardless of
    whether the job succeeded or failed.

    Args:
        job_id: The unique identifier for the processing job.
        zip_file_path: The absolute path to the uploaded ZIP file.
        streamer: The EventStreamer instance for real-time communication.
    """
    try:
        # The run_job function now receives the streamer instance directly.
        run_job(zip_file_path=zip_file_path, job_id=job_id, streamer=streamer)
    finally:
        # Clean up the uploaded file after the job is done (success or fail)
        if os.path.exists(zip_file_path):
            os.remove(zip_file_path)
            logging.info(f"Cleaned up uploaded file: {zip_file_path}")


# --- Socket.IO Event Handlers ---
@socketio.on('connect')
def handle_connect():
    """Handles a new client connection."""
    logging.info(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    """Handles a client disconnection."""
    logging.info(f"Client disconnected: {request.sid}")

@socketio.on('join')
def handle_join(data):
    """
    Handles a client's request to join a real-time event room.

    Clients must send a 'join' event with a 'job_id' to subscribe to
    the log events for a specific processing job. This ensures that clients
    only receive events relevant to their own upload.

    Args:
        data (dict): A dictionary from the client, expected to contain 'job_id'.
    """
    job_id = data.get('job_id')
    if job_id:
        join_room(job_id)
        logging.info(f"Client {request.sid} joined room {job_id}")
    else:
        logging.warning(f"Client {request.sid} tried to join without a job_id.")


# --- Main Execution ---
if __name__ == '__main__':
    # This is for local development only.
    # The Procfile uses gunicorn for production.
    # Note: debug=False prevents the reloader, which was causing issues.
    socketio.run(app, debug=False, port=5001)
