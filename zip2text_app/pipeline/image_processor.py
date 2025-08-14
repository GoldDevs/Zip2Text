"""
Pipeline component for scanning and validating images.

This module is responsible for traversing the extracted directory from the ZIP
file, identifying which files are supported images (e.g., JPG, PNG), and
logging which files are being included or skipped.
"""

import os
import logging
from typing import List, Tuple
from realtime.event_streamer import EventStreamer
from realtime.log_formatter import Severity

# Supported image formats as per the specification
SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.webp'}

def scan_for_images(
    extracted_dir_path: str,
    job_id: str,
    streamer: EventStreamer
) -> Tuple[List[str], int]:
    """
    Scans a directory for images, emitting real-time events for each finding.

    It walks through the directory tree, checks file extensions against a list
    of supported formats, and collects all valid image paths. It emits events
    for each image found and each file skipped.

    Args:
        extracted_dir_path: The path to the directory to scan.
        job_id: The unique ID for this job.
        streamer: The event streamer instance for sending real-time updates.

    Returns:
        A tuple containing:
        - A naturally sorted list of full paths to the found image files.
        - The total count of images found.
    """
    streamer.emit_event(
        job_id, 'IMAGE_SCAN', 'RUNNING', Severity.INFO,
        "Scanning extracted files for supported images..."
    )

    found_images = []
    skipped_count = 0

    for root, _, files in os.walk(extracted_dir_path):
        for filename in files:
            file_ext = os.path.splitext(filename)[1].lower()
            full_path = os.path.join(root, filename)

            if file_ext in SUPPORTED_FORMATS:
                streamer.emit_event(
                    job_id, 'IMAGE_FOUND', 'SUCCESS', Severity.INFO,
                    f"Found image: {filename}",
                    data={'filename': filename}
                )
                found_images.append(full_path)
            else:
                streamer.emit_event(
                    job_id, 'FILE_SKIPPED', 'RUNNING', Severity.DEBUG,
                    f"Skipped non-image file: {filename}",
                    data={'filename': filename}
                )
                skipped_count += 1

    found_images.sort()
    image_count = len(found_images)

    message = f"Scan complete. Found {image_count} supported images."
    if skipped_count > 0:
        message += f" Skipped {skipped_count} other files."

    streamer.emit_event(
        job_id, 'IMAGE_SCAN', 'SUCCESS', Severity.SUCCESS,
        message,
        data={'image_count': image_count, 'skipped_count': skipped_count}
    )

    return found_images, image_count
