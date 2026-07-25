import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict
import toml
from fastapi import UploadFile
from .models import JobResponse
from .exif import extract_exif

class JobManager:
    def __init__(self, config):
        self.root = Path(config.job_queue_root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.config = config

    def _next_id(self):
        existing = [int(p.name) for p in self.root.iterdir() if p.is_dir() and p.name.isdigit()]
        return max(existing, default=0) + 1

    def get_job_dir(self, job_id: int) -> Path:
        return self.root / str(job_id)

    def get_image_path(self, job_id: int, filename: str) -> Path:
        return self.get_job_dir(job_id) / filename

    async def create_job(self, images: List[UploadFile], title, vibe, hints, length, categories, model, use_exif):
        job_id = self._next_id()
        job_dir = self.get_job_dir(job_id)
        job_dir.mkdir(parents=True)

        # Save images
        image_names = []
        for idx, upload_file in enumerate(images, start=1):
            ext = ".jpg"
            # ensure JPEG (UI should send JPEG, but we convert just in case)
            content = await upload_file.read()
            # Optional: resize? UI already does it, but we can trust it.
            filename = f"image{idx}.jpg"
            file_path = job_dir / filename
            with open(file_path, "wb") as f:
                f.write(content)
            image_names.append(filename)

        # Extract EXIF if requested
        exif_data = ""
        if use_exif and image_names:
            first_image = job_dir / image_names[0]
            if first_image.exists():
                exif_data = extract_exif(first_image)

        # Parse categories (comma-separated or already list)
        if isinstance(categories, str):
            cats = [c.strip() for c in categories.split(",") if c.strip()]
        else:
            cats = categories

        # Write job.toml
        job_toml = {
            "id": job_id,
            "model": model,
            "title": title,
            "vibe": vibe,
            "hints": hints,
            "length": length,
            "categories": cats,
            "use_exif": use_exif,
            "exif_data": exif_data,
            "user_prompt": "",  # to be filled during processing
            "status": "pending",
            "marked": False,
            "created_at": datetime.utcnow().isoformat()
        }
        with open(job_dir / "job.toml", "w") as f:
            toml.dump(job_toml, f)

        return self._read_job(job_id)

    def list_jobs(self) -> List[JobResponse]:
        jobs = []
        for job_dir in sorted(self.root.iterdir(), key=lambda d: d.name):
            if job_dir.is_dir() and job_dir.name.isdigit():
                job_id = int(job_dir.name)
                job = self._read_job(job_id)
                if job:
                    jobs.append(job)
        return jobs

    def get_job(self, job_id: int) -> Optional[JobResponse]:
        return self._read_job(job_id)

    def _read_job(self, job_id: int) -> Optional[JobResponse]:
        job_dir = self.get_job_dir(job_id)
        job_file = job_dir / "job.toml"
        if not job_file.exists():
            return None
        with open(job_file, "r") as f:
            data = toml.load(f)
        # Get list of image files
        images = sorted([p.name for p in job_dir.glob("image*.jpg")])
        # Try to read story.txt
        story = None
        story_file = job_dir / "story.txt"
        if story_file.exists():
            story = story_file.read_text().strip()
        return JobResponse(
            id=job_id,
            status=data.get("status", "pending"),
            title=data.get("title", ""),
            vibe=data.get("vibe", ""),
            hints=data.get("hints", ""),
            length=data.get("length", "short"),
            categories=data.get("categories", []),
            model=data.get("model", ""),
            use_exif=data.get("use_exif", False),
            exif_data=data.get("exif_data", ""),
            story=story,
            images=images,
            marked=data.get("marked", False),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.utcnow().isoformat())),
            error_message=data.get("error_message")
        )

    def mark_job(self, job_id: int, marked: bool):
        job_dir = self.get_job_dir(job_id)
        job_file = job_dir / "job.toml"
        if not job_file.exists():
            return None
        with open(job_file, "r") as f:
            data = toml.load(f)
        data["marked"] = marked
        with open(job_file, "w") as f:
            toml.dump(data, f)
        return self._read_job(job_id)

    def delete_marked(self) -> int:
        count = 0
        for job in self.list_jobs():
            if job.marked:
                shutil.rmtree(self.get_job_dir(job.id))
                count += 1
        return count

    def remove_job(self, job_id: int):
        shutil.rmtree(self.get_job_dir(job_id), ignore_errors=True)

    def set_status(self, job_id: int, status: str, error_message: Optional[str] = None):
        job_dir = self.get_job_dir(job_id)
        job_file = job_dir / "job.toml"
        with open(job_file, "r") as f:
            data = toml.load(f)
        data["status"] = status
        if error_message:
            data["error_message"] = error_message
        with open(job_file, "w") as f:
            toml.dump(data, f)

    def save_story(self, job_id: int, story: str):
        job_dir = self.get_job_dir(job_id)
        (job_dir / "story.txt").write_text(story)
