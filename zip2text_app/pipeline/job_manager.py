"""
Manages the orchestration of the entire OCR processing pipeline.

This module is the main entry point for a new processing job. It calls each of
the individual pipeline components in the correct order, handles errors that
may occur during the process, and ensures that cleanup is performed.
"""

import logging
import os
import shutil

# Import pipeline components
from .zip_handler import handle_zip_file
from .image_processor import scan_for_images
from .vision_client import perform_ocr_on_images
from .text_aggregator import aggregate_text_results

# Import real-time components
from ..realtime.event_streamer import EventStreamer
from ..realtime.log_formatter import Severity

def run_job(zip_file_path: str, job_id: str, streamer: EventStreamer) -> str:
    """
    Orchestrates the entire Zip-to-Text pipeline, emitting real-time events.

    This function defines the main sequence of operations for an OCR job:
    1. Emit a 'JOB_STARTED' event.
    2. Unzip the file using `handle_zip_file`.
    3. Scan for images using `scan_for_images`.
    4. Perform OCR on images using `perform_ocr_on_images`.
    5. Aggregate results with `aggregate_text_results`.
    6. Emit a 'JOB_COMPLETED' or 'JOB_FAILED' event.
    It also ensures that the temporary directory is cleaned up.

    Args:
        zip_file_path: The path to the uploaded .zip file.
        job_id: A unique identifier for this job.
        streamer: An initialized EventStreamer instance.

    Returns:
        The final aggregated text or an error message.
    """
    if not streamer:
        logging.error(f"[{job_id}] Event streamer was not provided to run_job!")
        # We can't emit a failure event here, so we just return. The job will hang.
        return "Error: Server configuration issue."

    streamer.emit_event(
        job_id=job_id,
        event_name='JOB_STARTED',
        status='RUNNING',
        severity=Severity.INFO,
        message=f"Processing new job for file: {os.path.basename(zip_file_path)}"
    )

    extracted_dir = None
    try:
        # Pass job_id and streamer to each pipeline step
        extracted_dir = handle_zip_file(zip_file_path, job_id, streamer)

        image_paths, image_count = scan_for_images(extracted_dir, job_id, streamer)

        if image_count == 0:
            message = "Process complete. No supported image files (.jpg, .png, .webp) were found."
            streamer.emit_event(
                job_id=job_id,
                event_name='JOB_WARNING',
                status='COMPLETED',
                severity=Severity.WARNING,
                message=message
            )
            return message

        ocr_results = perform_ocr_on_images(image_paths, job_id, streamer)

        final_text = aggregate_text_results(image_paths, ocr_results, job_id, streamer)

        streamer.emit_event(
            job_id=job_id,
            event_name='JOB_COMPLETED',
            status='SUCCESS',
            severity=Severity.SUCCESS,
            message="Successfully processed all images.",
            data={'final_text': final_text}
        )
        return final_text

    except ValueError as e:
        error_message = f"A validation error occurred: {e}"
        streamer.emit_event(
            job_id=job_id, event_name='JOB_FAILED', status='FAILED',
            severity=Severity.ERROR, message=error_message
        )
        return f"Error: {e}"
    except Exception as e:
        error_message = f"An unexpected error occurred: {e}"
        logging.error(f"[{job_id}] {error_message}", exc_info=True)
        streamer.emit_event(
            job_id=job_id, event_name='JOB_FAILED', status='FAILED',
            severity=Severity.ERROR, message="An unexpected server error occurred."
        )
        return "An unexpected server error occurred. Please try again."
    finally:
        if extracted_dir and os.path.exists(extracted_dir):
            try:
                shutil.rmtree(extracted_dir)
                logging.info(f"[{job_id}] Cleaned up temporary directory {extracted_dir}")
            except Exception as e:
                logging.error(f"[{job_id}] Failed to cleanup directory {extracted_dir}: {e}")
