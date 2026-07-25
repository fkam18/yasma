from fastapi import BackgroundTasks
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from .config import load_config, save_config
from .models import (
    JobResponse, JobList, PostRequest, PostResponse,
    SettingsResponse, SettingsUpdate, LogResponse
)
from .jobs import JobManager
from .yapo import YapoClient
from .plugins import PluginManager
from .log import LogManager

app = FastAPI(title="YASMA")
config = load_config()
job_manager = JobManager(config)
yapo_client = YapoClient(config.yapo.url, config.yapo.api_token)
plugin_manager = PluginManager(config.plugins)
log_manager = LogManager()

# Mount static UI
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir, html=True), name="static")

    @app.get("/")
    async def root():
        return FileResponse(static_dir / "index.html")

# ---------- API Endpoints ----------

@app.get("/api/jobs", response_model=JobList)
def list_jobs():
    return {"jobs": job_manager.list_jobs()}

@app.post("/api/process")
async def process_all(background_tasks: BackgroundTasks):
    """Mark all pending jobs as 'processing' immediately, then process them in background."""
    pending_jobs = [j for j in job_manager.list_jobs() if j.status == "pending"]
    if not pending_jobs:
        return {"message": "No pending jobs"}

    # Instantly change status to 'processing'
    for job in pending_jobs:
        job_manager.set_status(job.id, "processing")

    def run_processing():
        for job in pending_jobs:
            try:
                # EXIF
                exif_data = ""
                if job.use_exif and job.images:
                    img_path = job_manager.get_image_path(job.id, job.images[0])
                    if img_path and img_path.exists():
                        from .exif import extract_exif
                        exif_data = extract_exif(img_path)

                user_prompt = (
                    f"Title: {job.title}\n"
                    f"Vibe: {job.vibe}\n"
                    f"Hints: {job.hints}\n"
                    f"Categories: {', '.join(job.categories)}\n"
                    f"Post Length: {job.length}\n"
                    f"EXIF Data: {exif_data if exif_data else '(none)'}\n\n"
                    f"You may use web search to find interesting facts about the photos if you think it will enrich the post."
                )

                attachments = [str(job_manager.get_image_path(job.id, img)) for img in job.images]

                story = yapo_client.submit_and_wait(
                    prompt=user_prompt,
                    model=job.model,
                    attachments=attachments,
                    job_name=f"yasma-{job.id}",
                    timeout=300
                )

                if story:
                    job_manager.save_story(job.id, story)
                    job_manager.set_status(job.id, "processed")
                    if config.auto_approve:
                        all_ok = True
                        for pname in config.plugins:
                            data = {
                                "title": job.title,
                                "story": story,
                                "image_paths": [str(job_manager.get_image_path(job.id, img)) for img in job.images],
                                "categories": job.categories
                            }
                            try:
                                res = plugin_manager.run_plugin(pname, data)
                                if res != "success":
                                    all_ok = False
                            except Exception:
                                all_ok = False
                        if all_ok:
                            job_manager.remove_job(job.id)
                            log_manager.log_post(job.id, job.title)
                else:
                    job_manager.set_status(job.id, "pending")  # revert so it can retry
                    log_manager.log_error(job.id, "LLM timeout/failure")
            except Exception as e:
                job_manager.set_status(job.id, "pending")
                log_manager.log_error(job.id, str(e))

    background_tasks.add_task(run_processing)
    return {"message": "Processing started"}

@app.post("/api/jobs", response_model=JobResponse, status_code=201)
async def create_job(
    images: list[UploadFile] = File(...),
    title: str = Form(""),
    vibe: str = Form(config.defaults.vibe),
    hints: str = Form(""),
    length: str = Form(config.defaults.length),
    categories: List[str] = Form(config.defaults.categories),   
    model: str = Form(config.defaults.model),
    use_exif: bool = Form(config.defaults.use_exif)
):
    job = await job_manager.create_job(images, title, vibe, hints, length, categories, model, use_exif)
    return job

@app.get("/api/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: int):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404)
    return job

@app.get("/api/jobs/{job_id}/images/{filename}")
def get_image(job_id: int, filename: str):
    path = job_manager.get_image_path(job_id, filename)
    if not path or not path.exists():
        raise HTTPException(404)
    return FileResponse(path)

@app.patch("/api/jobs/{job_id}/mark")
def mark_job(job_id: int, marked: bool = True):
    job = job_manager.mark_job(job_id, marked)
    if not job:
        raise HTTPException(404)
    return job

@app.post("/api/jobs/delete-marked")
def delete_marked():
    deleted = job_manager.delete_marked()
    return {"deleted": deleted}

@app.put("/api/jobs/{job_id}/post", response_model=PostResponse)
def post_job(job_id: int, req: PostRequest):
    job = job_manager.get_job(job_id)
    if not job or job.status != "processed":
        raise HTTPException(400, detail="Job not ready")
    results = {}
    for pname in req.plugins:
        if pname not in config.plugins:
            results[pname] = "fail (unknown plugin)"
            continue
        data = {
            "title": job.title,
            "story": job.story,
            "image_paths": [str(job_manager.get_image_path(job_id, img)) for img in job.images],
            "categories": job.categories
        }
        # Temporary debug
        import sys
        print(f"[DEBUG post_job] Plugin: {pname}", file=sys.stderr, flush=True)
        print(f"[DEBUG post_job] Data keys: {list(data.keys())}", file=sys.stderr, flush=True)
        print(f"[DEBUG post_job] image_paths: {data['image_paths']}", file=sys.stderr, flush=True)

        try:
            status = plugin_manager.run_plugin(pname, data)
            results[pname] = status
        except Exception as e:
            results[pname] = f"fail: {e}"
    if any(v == "success" for v in results.values()):
        job_manager.remove_job(job_id)
        log_manager.log_post(job_id, job.title)
    return {"results": results}

@app.get("/api/log", response_model=LogResponse)
def get_log(lines: int = 50):
    return {"log": log_manager.get_log(lines)}

@app.delete("/api/log", status_code=204)
def clear_log():
    log_manager.clear()

@app.get("/api/settings", response_model=SettingsResponse)
def get_settings():
    return {
        "auto_approve": config.auto_approve,
        "defaults": {
            "title": config.defaults.title,
            "vibe": config.defaults.vibe,
            "hints": config.defaults.hints,
            "categories": config.defaults.categories,
            "length": config.defaults.length,
            "use_exif": config.defaults.use_exif,
            "model": config.defaults.model,
            "post_plugins": config.defaults.post_plugins
        },
        "plugins": list(config.plugins.keys()),
        "allowed_categories": config.allowed_categories
    }

@app.put("/api/settings")
def update_settings(settings: SettingsUpdate):
    if settings.auto_approve is not None:
        config.auto_approve = settings.auto_approve
        save_config(config)
    return {"auto_approve": config.auto_approve}

@app.on_event("startup")
async def startup_scheduler():
    async def check_schedule():
        while True:
            now = datetime.now().strftime("%H:%M")
            if now in config.processing_times:
                # We cannot await async background tasks here easily, so just call the synchronous helper
                # Better: refactor into a shared function, but for simplicity we can call the endpoint logic directly
                pass  # You can leave this as a placeholder or remove it
            await asyncio.sleep(30)
    asyncio.create_task(check_schedule())

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3333)
