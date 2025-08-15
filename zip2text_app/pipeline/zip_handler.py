"""
Pipeline component for handling ZIP file validation and extraction.

This module is responsible for the first stage of the processing pipeline. It
ensures that the uploaded file is a valid ZIP archive and then securely
extracts its contents into a temporary directory for further processing.
"""

import os
import zipfile
import tempfile
import logging
import shutil
from ..realtime.event_streamer import EventStreamer
from ..realtime.log_formatter import Severity

def handle_zip_file(zip_file_path: str, job_id: str, streamer: EventStreamer) -> str:
    """
    Validates and extracts a ZIP archive, emitting real-time events.

    This function first checks if the file is a valid ZIP. If so, it creates
    a unique temporary directory and extracts the archive's contents into it,
    emitting events for the start and completion of validation and extraction.

    Args:
        zip_file_path: The path to the uploaded .zip file.
        job_id: The unique ID for this job.
        streamer: The event streamer instance for sending real-time updates.

    Returns:
        The path to the temporary directory where files were extracted.

    Raises:
        ValueError: If the file is not a valid or is a corrupt ZIP file.
    """
    streamer.emit_event(
        job_id, 'VALIDATION', 'RUNNING', Severity.INFO, "Validating uploaded file...")

    if not zipfile.is_zipfile(zip_file_path):
        streamer.emit_event(
            job_id, 'VALIDATION', 'FAILED', Severity.ERROR, "File is not a valid ZIP archive.")
        raise ValueError("Uploaded file is not a valid ZIP archive.")

    streamer.emit_event(
        job_id, 'VALIDATION', 'SUCCESS', Severity.SUCCESS, "File validation successful.")

    try:
        extraction_dir = tempfile.mkdtemp(prefix="zip2text_")
    except Exception as e:
        logging.error(f"[{job_id}] Failed to create temp directory: {e}")
        raise

    try:
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            streamer.emit_event(
                job_id, 'EXTRACTION', 'RUNNING', Severity.INFO,
                f"Starting extraction to temporary directory..."
            )

            # Extract and log each file individually
            file_list = zip_ref.infolist()
            for member in file_list:
                zip_ref.extract(member, extraction_dir)
                streamer.emit_event(
                    job_id, 'FILE_EXTRACTED', 'SUCCESS', Severity.INFO,
                    f"Extracted: {member.filename}",
                    data={'filename': member.filename}
                )

            streamer.emit_event(
                job_id, 'EXTRACTION', 'SUCCESS', Severity.SUCCESS,
                f"Extraction complete. Extracted {len(file_list)} items."
            )
    except zipfile.BadZipFile as e:
        shutil.rmtree(extraction_dir) # Clean up
        streamer.emit_event(
            job_id, 'EXTRACTION', 'FAILED', Severity.ERROR, "File is a corrupt ZIP archive.")
        raise ValueError(f"File is a corrupt or bad ZIP archive: {e}")
    except Exception as e:
        shutil.rmtree(extraction_dir) # Clean up
        streamer.emit_event(
            job_id, 'EXTRACTION', 'FAILED', Severity.ERROR, f"An unexpected error occurred during extraction.")
        logging.error(f"[{job_id}] Extraction error: {e}")
        raise

    return extraction_dir
