"""
chat_logger.py
--------------
Thread-safe logger that appends every chat message / event to a text file.

Format of each line:
    [DD-MM-YYYY HH:MM:SS] Username: message
    [DD-MM-YYYY HH:MM:SS] Rahul joined the chat.

The file is opened in APPEND mode ("a"), so old logs are never erased
when the server restarts.
"""
import os
import threading
from datetime import datetime

# chat_logs/ lives next to the server/ and client/ folders
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, "chat_logs")
LOG_FILE = os.path.join(LOG_DIR, "chat_log.txt")


class ChatLogger:
    def __init__(self, log_file=LOG_FILE):
        self.log_file = log_file
        # Many client threads log at the same time -> protect the file with a lock
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

    @staticmethod
    def timestamp():
        return datetime.now().strftime("%d-%m-%Y %H:%M:%S")

    def _write(self, text):
        line = f"[{self.timestamp()}] {text}\n"
        try:
            with self._lock:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(line)
        except OSError as err:
            # Logging must never crash the server
            print(f"[LOGGER ERROR] Could not write to log file: {err}")

    def log_message(self, username, message):
        """Log a normal chat message."""
        self._write(f"{username}: {message}")

    def log_event(self, event):
        """Log a system event (join, leave, server start/stop)."""
        self._write(event)
