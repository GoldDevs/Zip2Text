# Manages real-time event broadcasting (e.g., via Socket.IO).

import logging
from flask_socketio import SocketIO
from typing import Optional, Dict, Any

from realtime.log_formatter import format_event, Severity

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class EventStreamer:
    """
    A handler for formatting and emitting real-time events to clients via Socket.IO.
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
        Formats an event and emits it to a specific client room.

        Args:
            job_id: The unique ID for the job, used as the Socket.IO room.
            event_name: The machine-readable name of the event.
            status: The status of the event (e.g., 'RUNNING', 'SUCCESS').
            severity: The severity level of the event.
            message: A human-readable message.
            data: Optional dictionary with additional data.
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

# A global instance that can be initialized by the main app
# This is a simple approach. In larger apps, Flask's app context might be used.
event_streamer: Optional[EventStreamer] = None

def initialize_event_streamer(socketio: SocketIO):
    """Initializes the global event streamer instance."""
    global event_streamer
    if not event_streamer:
        event_streamer = EventStreamer(socketio)
    return event_streamer
