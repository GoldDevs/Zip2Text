"""
Formats log messages into a standardized JSON structure for real-time events.

This module provides a consistent structure for all log events that are sent
to the client. This ensures that the frontend can reliably parse and display
log messages from different parts of the backend pipeline.
"""

import datetime
from enum import Enum
from typing import Optional, Dict, Any

class Severity(Enum):
    """
    Enumeration for log severity levels.

    This provides a controlled vocabulary for event severities, which can be
    used by the frontend to apply different styles to log messages (e.g.,
    coloring them based on whether they are an error, warning, or success).
    """
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"
    DEBUG = "DEBUG"

def format_event(
    event_name: str,
    status: str,
    severity: Severity,
    message: str,
    data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Creates a standardized dictionary for a real-time event.

    This function is the single source of truth for the structure of log
    events sent to the client. It includes a timestamp, event name, status,
    severity, a human-readable message, and any additional data.

    Args:
        event_name: The machine-readable name of the event (e.g., 'JOB_STARTED').
        status: The current status of the event (e.g., 'RUNNING', 'SUCCESS').
        severity: The severity level of the event from the Severity enum.
        message: A human-readable message describing the event.
        data: An optional dictionary for additional payload data.

    Returns:
        A dictionary representing the structured event log, ready to be
        serialized to JSON.
    """
    if data is None:
        data = {}

    event_payload = {
        'timestamp': datetime.datetime.utcnow().isoformat() + 'Z', # Use Z for UTC
        'event': event_name,
        'status': status,
        'severity': severity.value,
        'message': message,
        'data': data
    }
    return event_payload
