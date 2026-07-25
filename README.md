# YASMA – Yet Another Social Media Assistant

AI-powered social media post generator that turns your photos into ready‑to‑publish stories, using a self‑hosted LLM backend (YAPO). Deploy it at home, review, tweak, and post to multiple platforms with one click.

## Features

- **Visual AI Storyteller** – Combine 1–N photos with a title, vibe, hints, and EXIF data to generate engaging social media posts via YAPO.
- **Review & Approve** – All posts land in an approval queue; you can edit or discard before publishing.
- **Plugin System** – WordPress already built; extend with custom scripts for Facebook, Instagram, Signal, etc.
- **One‑Page UI** – Responsive SPA for desktop and mobile browsers; pre‑filled defaults reduce friction.
- **Home‑Lab Ready** – Runs in Docker, communicates via HTTP (use VPN externally), deployed with Ansible.
- **Auto‑Refresh** – Job list updates every 5 s; “Process All Now” runs LLM generation in the background.

## Architecture

User Photos → YASMA (API + UI) → YAPO (LLM) → Generated Story
↓
Review & Post → Plugins → Social Media
text


- **YASMA** – FastAPI backend + vanilla JS frontend.
- **YAPO** – External job queue for LLM tasks (uses visual models and web search).
- **Plugins** – Standalone Python scripts called dynamically (no import caching).

## Prerequisites

- Docker and Docker Compose (plugin version)
- YAPO instance running (with a `yasma` model type configured)
- Ansible (only for deployment to a remote server)
- WordPress site with Application Passwords (if using the WP plugin)

## Installation

```bash
git clone https://github.com/yourusername/yasma.git
cd yasma
cp config.toml.example config.toml    # edit with your YAPO URL, token, etc.
mkdir secrets && cp secrets/wp_post.toml.example secrets/wp_post.toml  # add WP creds
./build.sh
./deploy-to-app.sh                    # deploys to app2.alt (edit ansible/inventory.ini)

The UI will be available at http://<host>:3333.
Configuration

All settings live in config.toml (mounted into the container). Key sections:
toml

[yapo]
url = "http://192.168.0.15:3388"
api_token = "your-token"
default_model = "yasma"

[defaults]
title = "Check it out"
vibe = "Documentary"
hints = "Today, UK, Event"
categories = ["general"]
length = "short"
use_exif = true
model = "yasma"
post_plugins = ["wordpress"]   # pre-checked plugins on the review card

allowed_categories = ["general", "food", "travel", "event", "nature", "tech"]

[plugins.wordpress]
script = "wp_post.py"
config = "/app/secrets/wp_post.toml"

    processing_times – cron‑like times (e.g., ["10:00", "15:00"]) for automatic LLM generation.

    auto_approve – if true, posts are published immediately after generation (to all plugins).

Plugin credentials go into secrets/ (gitignored). Example for WordPress:
toml

# secrets/wp_post.toml
[wordpress]
url = "https://yourblog.com"
username = "your-username"
password = "your-application-password"

Usage
Create a Post

    Go to the Create Job tab.

    Upload images (JPEG, automatically resized to 1024 px wide).

    Adjust title, vibe, hints, categories, length, and EXIF toggle (all pre‑filled from defaults).

    Click Create Job – it appears as pending.

Generate Story

    Manual: Click Process All Now – status changes to processing, then processed when done.

    Automatic: The background scheduler will process pending jobs at the configured times.

Review & Post

    In the job list, processed jobs show the generated story and plugin checkboxes (e.g., WordPress).

    Select desired plugins and click Post.

    The job is removed after at least one successful post; failures leave it in processed for retry.

Log

    The Log tab shows timestamps of posted jobs and LLM errors.

    Use Erase Log to clear the history.

Plugins

Plugins are Python scripts placed in the plugins/ directory inside the container. They receive a JSON object with title, story, image_paths (array of absolute file paths), and categories, and must return {"status": "success"} or {"status": "fail", "reason": "..."}.

The WordPress plugin (wp_post.py) is a complete example – it uploads the first image as the featured image, creates a new post, and handles category mapping.

To add a new platform:

    Create a script (e.g., instagram_post.py) implementing a post(data) function.

    Add it to config.toml under [plugins].

    Provide its credentials in secrets/ if needed.

REST API Summary
Method	Endpoint	Description
GET	/api/jobs	List all jobs
POST	/api/jobs	Create a new job (multipart form)
GET	/api/jobs/{id}	Job detail
GET	/api/jobs/{id}/images/{filename}	Serve a job image
PATCH	/api/jobs/{id}/mark	Toggle deletion mark
POST	/api/jobs/delete-marked	Delete all marked jobs
PUT	/api/jobs/{id}/post	Post to selected plugins
POST	/api/process	Start background LLM processing
GET	/api/log	Get log (query ?lines=100)
DELETE	/api/log	Clear log
GET	/api/settings	Current config defaults
PUT	/api/settings	Update auto_approve

All responses are JSON. The UI communicates exclusively through these endpoints.
Deployment

The project includes an Ansible playbook and a build script for easy deployment:
text

./build.sh                # Builds Docker image and exports yasma.tar.gz
./deploy-to-app.sh        # Copies files to app2.alt, loads image, starts container

The Docker Compose file uses a bridged network with a custom DNS (192.168.0.15), mounts host directories for config.toml and secrets/, and persists job data in a named volume (yasma_data).

For persistent jobs across redeployments, the playbook runs docker compose down (without --volumes) followed by docker compose up -d.
Contributing

Contributions are welcome! Please open an issue or pull request. For local development:

    Clone the repo and set up a Python venv with the dependencies in requirements.txt.

    Run uvicorn yasma.main:app --reload --port 3333 for hot‑reloading.

    Place your test images in a local data/jobs/ folder (mirroring the container structure).

License

MIT 
