"""
Manages real-time event broadcasting using Flask-SocketIO.

This module provides the EventStreamer class, which is a wrapper around the
Socket.IO instance. It is used by the backend pipeline to send structured,
real-time log events to the correct client.
"""

import logging
from flask_socketio import SocketIO
from typing import Optional, Dict, Any

from .log_formatter import format_event, Severity

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class EventStreamer:
    """
    A handler for formatting and emitting real-time events to clients.

    This class abstracts the details of formatting a log event and sending it
    to a specific Socket.IO room, identified by the job_id.
    """
    def __init__(self, socketio: SocketIO):
        """
        Initializes the EventStreamer with a Flask-SocketIO instance.

        Args:
            socketio: The active Flask-SocketIO server instance.
        """
        self.socketio = socketio

    def emit_event(
        self,
        job_id: str,
        event_name: str,
        status: str,
        severity: Severity,
        message: str,
        data: Optional[Dict[str, Any]] = None
    ):
        """
        Formats an event and emits it to a specific client room via Socket.IO.

        The event is structured using `format_event` and then broadcast to the
        room that matches the `job_id`. The client-side application listens for
        the 'new_log' event to receive these updates.

        Args:
            job_id: The unique ID for the job, used as the Socket.IO room.
            event_name: The machine-readable name of the event (e.g., 'OCR_STARTED').
            status: The status of the event (e.g., 'RUNNING', 'SUCCESS').
            severity: The severity level of the event (e.g., Severity.INFO).
            message: A human-readable message for the log.
            data: Optional dictionary with additional structured data.
        """
        try:
            # 1. Format the event into a standard structure
            payload = format_event(
                event_name=event_name,
                status=status,
                severity=severity,
                message=message,
                data=data
            )

            # 2. Emit the event to the client's room
            # The frontend will listen for the 'new_log' event.
            self.socketio.emit('new_log', payload, room=job_id)

            # Optional: Log the event to the server console as well for debugging
            logging.info(f"Emitted to room {job_id}: {message}")

        except Exception as e:
            logging.error(f"Failed to emit event to room {job_id}: {e}")

# The global instance pattern is removed in favor of dependency injection.

def create_event_streamer(socketio: SocketIO) -> "EventStreamer":
    """
    Factory function to create an instance of the EventStreamer.

    This approach allows the application to create and pass the EventStreamer
    instance explicitly, which avoids potential issues with global state when
    using background workers (like eventlet).

    Args:
        socketio: The active Flask-SocketIO server instance.

    Returns:
        A new instance of the EventStreamer class.
    """
    return EventStreamer(socketio)
