# Client for interacting with the Google Cloud Vision API.

import os
import json
import logging
from typing import List, Dict

# Import Google Cloud libraries
from google.cloud import vision
from google.oauth2 import service_account

# Import project components
from realtime.event_streamer import EventStreamer
from realtime.log_formatter import Severity

def _initialize_vision_client():
    """
    Initializes the Vision API client from environment variables.
    Raises:
        EnvironmentError: If credentials are not set or invalid.
    """
    credentials_json_str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if not credentials_json_str:
        raise EnvironmentError("GOOGLE_APPLICATION_CREDENTIALS_JSON environment variable is not set.")

    try:
        credentials_info = json.loads(credentials_json_str)
        credentials = service_account.Credentials.from_service_account_info(credentials_info)
        client = vision.ImageAnnotatorClient(credentials=credentials)
        logging.info("Google Cloud Vision client initialized successfully for this job.")
        return client
    except Exception as e:
        logging.critical(f"Failed to initialize Google Vision client: {e}")
        raise EnvironmentError(f"Failed to initialize Google Vision client: {e}")

def perform_ocr_on_images(
    image_paths: List[str],
    job_id: str,
    streamer: EventStreamer
) -> Dict[str, str]:
    """
    Performs OCR on a list of images using the Google Cloud Vision API.

    Args:
        image_paths: A list of full paths to the image files.
        job_id: The unique ID for this job.
        streamer: The event streamer instance.

    Returns:
        A dictionary mapping image paths to their OCR text.

    Raises:
        EnvironmentError: If the Google Cloud client cannot be initialized.
    """
    streamer.emit_event(
        job_id, 'OCR_PIPELINE', 'RUNNING', Severity.INFO,
        f"Starting OCR process for {len(image_paths)} images..."
    )

    try:
        client = _initialize_vision_client()
    except EnvironmentError as e:
        # This is a critical failure. The job cannot proceed.
        streamer.emit_event(
            job_id, 'OCR_PIPELINE', 'FAILED', Severity.ERROR,
            f"Configuration error: Could not initialize Vision API. Please check server credentials. Error: {e}"
        )
        # Re-raise the exception to be caught by the job manager, which will terminate the job.
        raise

    ocr_results = {}
    total_images = len(image_paths)

    for i, image_path in enumerate(image_paths):
        filename = os.path.basename(image_path)

        streamer.emit_event(
            job_id, 'OCR_STARTED', 'RUNNING', Severity.INFO,
            f"({i+1}/{total_images}) Processing: {filename}",
            data={'filename': filename, 'current': i+1, 'total': total_images}
        )

        try:
            with open(image_path, "rb") as image_file:
                content = image_file.read()

            image = vision.Image(content=content)
            response = client.document_text_detection(image=image)

            if response.error.message:
                raise Exception(response.error.message)

            text = response.full_text_annotation.text
            ocr_results[image_path] = text

            streamer.emit_event(
                job_id, 'OCR_SUCCESS', 'SUCCESS', Severity.SUCCESS,
                f"({i+1}/{total_images}) Successfully processed: {filename}",
                data={'filename': filename}
            )
        except Exception as e:
            # Handle failure for a single image, but continue with the rest.
            error_message = f"Could not process image {filename} with Vision API: {e}"
            logging.error(f"[{job_id}] {error_message}")
            streamer.emit_event(
                job_id, 'OCR_FAILED', 'FAILED', Severity.ERROR,
                f"({i+1}/{total_images}) Failed to process: {filename}. Error: {e}",
                data={'filename': filename, 'error': str(e)}
            )
            # Add a placeholder to the results so the aggregator knows it failed.
            ocr_results[image_path] = f"[Error processing {filename}: See server logs for details]"


    streamer.emit_event(
        job_id, 'OCR_PIPELINE', 'SUCCESS', Severity.SUCCESS,
        "Finished processing all images."
    )
    return ocr_results
