"""
Pipeline component for aggregating final text results.

This is the final stage of the OCR pipeline. It takes the text results from
all processed images and combines them into a single, ordered text block.
"""

import logging
from typing import List, Dict
from realtime.event_streamer import EventStreamer
from realtime.log_formatter import Severity

def aggregate_text_results(
    sorted_image_paths: List[str],
    ocr_results: Dict[str, str],
    job_id: str,
    streamer: EventStreamer
) -> str:
    """
    Aggregates OCR text from multiple images into a single string.

    It iterates through the sorted list of image paths to ensure the final
    text is in the correct order. It retrieves the OCR text for each path
    from the results dictionary and joins them.

    Args:
        sorted_image_paths: A list of image paths, sorted in the desired
                            order for the final output.
        ocr_results: A dictionary mapping image paths to their OCR text.
        job_id: The unique ID for this job.
        streamer: The event streamer instance.

    Returns:
        A single string containing all aggregated text, with each part
        separated by double newlines.
    """
    streamer.emit_event(
        job_id, 'AGGREGATION', 'RUNNING', Severity.INFO,
        "Aggregating text from all processed images..."
    )

    final_text_parts = []
    for image_path in sorted_image_paths:
        text = ocr_results.get(image_path)
        if text:
            final_text_parts.append(text)
        else:
            logging.warning(f"[{job_id}] Could not find OCR result for {image_path} during aggregation.")

    # Join with a double newline for clear separation between pages.
    final_text_output = "\n\n".join(final_text_parts)

    streamer.emit_event(
        job_id, 'AGGREGATION', 'SUCCESS', Severity.SUCCESS,
        "Text aggregation complete."
    )

    return final_text_output
