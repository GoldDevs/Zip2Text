# Formats log messages into a standardized JSON structure.

import datetime
from enum import Enum
from typing import Optional, Dict, Any

class Severity(Enum):
    """Enumeration for log severity levels."""
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

    Args:
        event_name: The machine-readable name of the event (e.g., 'JOB_STARTED').
        status: The current status of the event (e.g., 'RUNNING', 'SUCCESS', 'FAILED').
        severity: The severity level of the event.
        message: A human-readable message describing the event.
        data: An optional dictionary for additional payload data.

    Returns:
        A dictionary representing the structured event log.
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
