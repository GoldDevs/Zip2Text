# MOCKED client for interacting with the Google Cloud Vision API.

import os
import logging
import time
from typing import List, Dict
from realtime.event_streamer import EventStreamer
from realtime.log_formatter import Severity

def perform_ocr_on_images(
    image_paths: List[str],
    job_id: str,
    streamer: EventStreamer
) -> Dict[str, str]:
    """
    MOCKED: Simulates performing OCR, emitting real-time events.

    Args:
        image_paths: A list of full paths to the image files.
        job_id: The unique ID for this job.
        streamer: The event streamer instance.

    Returns:
        A dictionary mapping image paths to their mocked OCR text.
    """
    streamer.emit_event(
        job_id, 'OCR_PIPELINE', 'RUNNING', Severity.INFO,
        f"Starting OCR process for {len(image_paths)} images..."
    )

    ocr_results = {}
    total_images = len(image_paths)

    for i, image_path in enumerate(image_paths):
        filename = os.path.basename(image_path)

        streamer.emit_event(
            job_id, 'OCR_STARTED', 'RUNNING', Severity.INFO,
            f"({i+1}/{total_images}) Processing: {filename}",
            data={'filename': filename, 'current': i+1, 'total': total_images}
        )

        # Simulate network latency and processing time of an API call
        time.sleep(1.5)

        # In a real scenario, you would add try/except blocks here for API errors
        try:
            # MOCKED RESPONSE
            mocked_text = f"--- Page: {filename} ---\nThis is the simulated OCR text content for the image '{filename}'.\n"

            ocr_results[image_path] = mocked_text

            streamer.emit_event(
                job_id, 'OCR_SUCCESS', 'SUCCESS', Severity.SUCCESS,
                f"({i+1}/{total_images}) Successfully processed: {filename}",
                data={'filename': filename}
            )
        except Exception as e:
            # This block would handle real API call failures
            streamer.emit_event(
                job_id, 'OCR_FAILED', 'FAILED', Severity.ERROR,
                f"({i+1}/{total_images}) Failed to process: {filename}",
                data={'filename': filename, 'error': str(e)}
            )

    streamer.emit_event(
        job_id, 'OCR_PIPELINE', 'SUCCESS', Severity.SUCCESS,
        "Finished processing all images."
    )
    return ocr_results
