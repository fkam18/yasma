*** YASMA - Yet Another Social Media Assistant  
* Version: 04

---

** Key Functions
- YASMA uses YAPO (https://github.com/fkam18/yapo) API to create social media posts from user‑supplied photos and hints.
- Targets a home self‑hosted AI environment.
- Posts sit in an approval queue before publishing.
- Auto‑approve option available (see Workflow).
- Social media plugins are user‑defined scripts (WordPress implemented, others pending).
- Single‑page web app for Android & desktop (Firefox/Chromium).

---

## Technical Implementation
- Docker container with a named volume (`yasma_data`) for job queue and assets.
- UI communicates via HTTP REST API on port **3333**.
- Only HTTP (no HTTPS); intended for use behind OpenVPN when accessing externally.
- Ansible deploys the container to an in‑house Docker server.

---

## UI
- Reactive, adapts to different screen sizes.
- Job creation screen with minimal fields:
  - **Images** (required, multiple) – resized to 1024 px wide by the UI before upload.
  - **Title**, **Vibe**, **Hints**, **Categories** (multi‑select dropdown), **Post Length**, **Model**, **Use EXIF** – all pre‑filled from `config.toml` defaults.
- Job list shows status: `pending`, `processing`, `processed`, `error`, `posted`.
- For processed jobs, inline plugin checkboxes appear next to a **Post** button; defaults for checked plugins come from `config.toml` (`post_plugins`).
- “Marked for delete” checkbox and “Delete All Marked” button.
- Jobs are removed immediately after a successful post to at least one plugin.
- Auto‑refresh of job list every 5 seconds.
- Log tab with date/time, job number, title, and posting status; can be fully erased.

---

## Workflow

### Processing
- Scheduled processing times are defined in `config.toml` (`processing_times`).
- Manual “Process All Now” button instantly sets all `pending` jobs to `processing` and starts a background task.
- Processing:
  1. Extracts EXIF (if enabled) from the first image.
  2. Builds a user prompt from title, vibe, hints, categories, length, EXIF.
  3. Submits the prompt + images (base64‑encoded) to YAPO with a unique name (`yasma-{job_id}`).
  4. Waits for YAPO to finish (blocking call, up to 300s).
  5. On success: saves story, sets status to `processed`.
  6. If `auto_approve` is true, automatically posts to all plugins and removes the job.
- If YAPO fails, the job reverts to `pending` (retried later).

### Posting
- Only manually triggered from the UI for jobs in `processed` state.
- User selects one or more plugins and clicks **Post**.
- The plugin receives JSON: `title`, `story`, `image_paths` (array of absolute file paths), `categories`.
- On success, the job is removed; on failure, the job stays `processed` for retry.

### Job Lifecycle
- `pending` → no `story.txt`, awaiting LLM.
- `processing` → background task running; UI shows blue badge.
- `processed` → `story.txt` exists, ready for posting.
- `error` → LLM failed, error logged; job remains `pending` for retry.
- `posted` → removed from queue (logged).

---

## How YASMA Calls YAPO
- YASMA sends requests to YAPO’s `/api/submit` with a JSON payload containing the prompt, model type, and base64‑encoded images.
- It then polls `/api/job/{qno}?wait=true&timeout=300` for completion.
- The raw output is parsed: if it is a JSON object with a `content` field (chat‑style response), only that text is used as the story; otherwise the whole output is taken.

---

## Configuration

### `config.toml` (on server)
```toml
processing_times = ["10:00", "15:00", "22:00"]

[yapo]
url = "http://192.168.0.15:3388"   # YAPO API address
api_token = "your-token"
default_model = "yasma"

job_queue_root = "/data/jobs"
auto_approve = false

[defaults]
title = "Check it out"
vibe = "Documentary"
hints = "Today, UK, Event"
categories = ["general"]
length = "short"
use_exif = true
model = "yasma"
post_plugins = ["wordpress"]       # pre‑checked plugins for posting

allowed_categories = ["general", "food", "travel", "event", "nature", "tech"]

[plugins.wordpress]
script = "wp_post.py"
config = "/app/secrets/wp_post.toml"   # path inside container

    plugins section uses an extended format: each plugin is a sub‑table with script and (optional) config.

    allowed_categories is the master list; defaults.categories are pre‑selected.

job.toml (inside job folder)
toml

id = 1
model = "yasma"
title = "Sunset at the lake"
vibe = "calm and poetic"
hints = "focus on the reflection in the water"
length = "short"
categories = ["travel", "nature"]
use_exif = true
exif_data = ""
user_prompt = ""
status = "pending"

Plugin Specification

    Plugin scripts reside in plugins/ inside the container.

    They are loaded via exec() to avoid any import caching.

    Input JSON:
    json

    {
      "title": "…",
      "story": "…",
      "image_paths": ["/data/jobs/1/image1.jpg", …],
      "categories": ["travel", "nature"]
    }

    Output JSON:
    json

    {"status": "success"}

    or
    json

    {"status": "fail", "reason": "error message"}

    The plugin reads its own credentials from a mounted secrets file (e.g., /app/secrets/wp_post.toml).

REST API Summary

    GET /api/jobs – list jobs

    POST /api/jobs – create job (multipart form: images, title, vibe, hints, length, categories, model, use_exif)

    GET /api/jobs/{id} – job detail

    GET /api/jobs/{id}/images/{filename} – serve image

    PATCH /api/jobs/{id}/mark – toggle deletion mark

    POST /api/jobs/delete-marked – delete all marked jobs

    PUT /api/jobs/{id}/post – post to selected plugins (body: {"plugins": ["wordpress"]})

    POST /api/process – start background processing, returns {"message": "Processing started"}

    GET /api/log?lines=100 – recent log entries

    DELETE /api/log – clear log

    GET /api/settings – current settings and defaults

    PUT /api/settings – update auto_approve

Deployment

    Build: ./build.sh creates a Docker image and exports docker/yasma.tar.gz.

    Deploy: ./deploy-to-app.sh copies the archive, config, secrets, and docker-compose.yml to app2.alt via Ansible, then runs docker compose up -d.

    Docker Compose (docker/docker-compose.yml):

        Uses bridge networking with custom DNS 192.168.0.15.

        Mounts host directories for config and secrets (read‑only).

        Named volume yasma_data for job storage.

        Environment: YASMA_CONFIG=/app/config.toml, PYTHONDONTWRITEBYTECODE=1.

    Ansible inventory: app2.alt ansible_user=master (passwordless SSH).

Project Structure
text

yasma/
├── ansible/
│   ├── inventory.ini
│   └── deploy.yml
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── plugins/
│   └── wp_post.py
├── secrets/              # gitignored
├── static/
│   └── index.html
├── yasma/                # backend Python package
├── config.toml           # (on server)
├── build.sh
├── deploy-to-app.sh
└── requirements.txt

System Prompt (in YAPO)

The model type yasma should use a system prompt that instructs the LLM to:

    Analyse photos for landmarks, artefacts, etc.

    Perform up to 2 web searches for factual enrichment.

    Compose a post matching the requested vibe, incorporating EXIF details if available, and respecting the length limits.

    Output only the final post, no extra commentary.

(Full prompt text as in spec03.md.)
