# Manages the entire OCR pipeline from start to finish.

import logging
import os
import shutil

# Import pipeline components
from pipeline.zip_handler import handle_zip_file
from pipeline.image_processor import scan_for_images
from pipeline.vision_client import perform_ocr_on_images
from pipeline.text_aggregator import aggregate_text_results

# Import real-time components
from realtime.event_streamer import event_streamer # Use the initialized global instance
from realtime.log_formatter import Severity

def run_job(zip_file_path: str, job_id: str) -> str:
    """
    Orchestrates the entire Zip-to-Text pipeline, emitting real-time events.

    Args:
        zip_file_path: The path to the uploaded .zip file.
        job_id: A unique identifier for this job.

    Returns:
        The final aggregated text or an error message.
    """
    if not event_streamer:
        logging.error("Event streamer is not initialized!")
        return "Error: Server configuration issue."

    event_streamer.emit_event(
        job_id=job_id,
        event_name='JOB_STARTED',
        status='RUNNING',
        severity=Severity.INFO,
        message=f"Processing new job for file: {os.path.basename(zip_file_path)}"
    )

    extracted_dir = None
    try:
        # Pass job_id and streamer to each pipeline step
        extracted_dir = handle_zip_file(zip_file_path, job_id, event_streamer)

        image_paths, image_count = scan_for_images(extracted_dir, job_id, event_streamer)

        if image_count == 0:
            message = "Process complete. No supported image files (.jpg, .png, .webp) were found."
            event_streamer.emit_event(
                job_id=job_id,
                event_name='JOB_WARNING',
                status='COMPLETED',
                severity=Severity.WARNING,
                message=message
            )
            return message

        ocr_results = perform_ocr_on_images(image_paths, job_id, event_streamer)

        final_text = aggregate_text_results(image_paths, ocr_results, job_id, event_streamer)

        event_streamer.emit_event(
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
        event_streamer.emit_event(
            job_id=job_id, event_name='JOB_FAILED', status='FAILED',
            severity=Severity.ERROR, message=error_message
        )
        return f"Error: {e}"
    except Exception as e:
        error_message = f"An unexpected error occurred: {e}"
        logging.error(error_message, exc_info=True)
        event_streamer.emit_event(
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
