from pathlib import Path
from datetime import datetime

LOG_PATH = Path("/tmp/yasma.log")

class LogManager:
    def __init__(self):
        LOG_PATH.touch(exist_ok=True)

    def log_post(self, job_id: int, title: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_PATH, "a") as f:
            f.write(f"{timestamp} - Job #{job_id} '{title}' posted\n")

    def log_error(self, job_id: int, error: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_PATH, "a") as f:
            f.write(f"{timestamp} - Job #{job_id} Yapo error: {error} (will retry)\n")

    def get_log(self, lines: int = 50) -> list:
        if not LOG_PATH.exists():
            return []
        with open(LOG_PATH, "r") as f:
            all_lines = f.readlines()
        return [line.rstrip() for line in all_lines[-lines:]]

    def clear(self):
        LOG_PATH.write_text("")
