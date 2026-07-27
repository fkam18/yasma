import requests
import re
import time
import base64
import mimetypes
import json
from pathlib import Path
from typing import List, Optional

class YapoClient:
    def __init__(self, base_url, api_token=None):
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.headers = {"Content-Type": "application/json"}

    def _encode_attachments(self, file_paths: List[str]) -> List[dict]:
        attachments = []
        for path_str in file_paths:
            path = Path(path_str)
            if not path.exists():
                continue
            mime_type, _ = mimetypes.guess_type(path)
            if mime_type is None:
                mime_type = "application/octet-stream"
            with open(path, "rb") as f:
                content = base64.b64encode(f.read()).decode("utf-8")
            attachments.append({
                "filename": path.name,
                "content": content,
                "mime": mime_type
            })
        return attachments

    def _extract_text(self, raw_output: str) -> Optional[str]:
        """Extract post text from YAPO's output (handles chat‑JSON)."""
        if not raw_output:
            return None
        try:
            data = json.loads(raw_output)
            if isinstance(data, dict) and "content" in data:
                text = data["content"].strip()
            else:
                text = raw_output.strip()
        except (json.JSONDecodeError, TypeError):
            text = raw_output.strip()

        if not text:
            return None

        # Remove everything up to the last </think> tag (inclusive)
        cleaned = re.sub(r'^.*</think>\s*', '', text, flags=re.DOTALL)

        return cleaned.strip()

    def submit_and_wait(self, prompt, model, attachments=None, job_name="yasma-job", timeout=300) -> Optional[str]:
        encoded_attachments = self._encode_attachments(attachments or [])
        payload = {
            "prompt": prompt,
            "mtype": model,
            "name": job_name,
            "attachments": encoded_attachments
        }

        # Submit job
        try:
            resp = requests.post(
                f"{self.base_url}/api/submit",
                json=payload,
                headers=self.headers,
                timeout=30
            )
            resp.raise_for_status()
            data = resp.json()
            if not data.get("success"):
                return None
            qno = data["qno"]
        except Exception:
            return None

        # Wait for completion using YAPO's blocking wait endpoint
        try:
            resp = requests.get(
                f"{self.base_url}/api/job/{qno}?wait=true&timeout={timeout}",
                timeout=timeout + 10
            )
            if resp.status_code == 200:
                job_data = resp.json()
                state = job_data.get("state", "").lower()
                if state == "done":
                    raw_output = job_data.get("output", "")
                    return self._extract_text(raw_output)
                # else fall through to fallback
        except Exception:
            pass   # fallback to polling

        # Fallback: poll manually every 2 seconds if the blocking call failed
        start = time.time()
        while time.time() - start < timeout:
            try:
                resp = requests.get(f"{self.base_url}/api/job/{qno}", timeout=10)
                if resp.status_code == 200:
                    job_data = resp.json()
                    state = job_data.get("state", "").lower()
                    if state == "done":
                        raw_output = job_data.get("output", "")
                        return self._extract_text(raw_output)
                    elif state == "error":
                        return None
                time.sleep(2)
            except Exception:
                time.sleep(2)

        return None
