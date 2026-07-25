import toml, json, base64, tempfile, os, sys
from pathlib import Path
import requests
from requests.auth import HTTPBasicAuth
from PIL import Image
from io import BytesIO

DEFAULT_CONFIG_PATH = "/app/secrets/wp_post.toml"

def _log(msg):
    """Write debug info to stderr so it appears in docker logs."""
    print(f"[wp_post] {msg}", file=sys.stderr, flush=True)

def _load_config():
    config_path = Path(DEFAULT_CONFIG_PATH)
    if not config_path.exists():
        raise FileNotFoundError(f"Missing secrets file: {config_path}")
    cfg = toml.load(config_path)
    wp = cfg.get("wordpress", {})
    if not all(k in wp for k in ("url", "username", "password")):
        raise ValueError("Secrets file must contain [wordpress] with url, username, password")
    return wp

def _image_to_jpeg_bytes(image_input, max_bytes=2_000_000):
    """
    Convert image_input (file path or dict) to JPEG bytes ≤ max_bytes.
    """
    # Load image
    if isinstance(image_input, dict):
        b64_content = image_input['content']
        raw_bytes = base64.b64decode(b64_content)
        img = Image.open(BytesIO(raw_bytes))
    else:
        img = Image.open(image_input)

    # Convert to RGB if necessary
    if img.mode in ('RGBA', 'LA') or (img.mode == 'P'):
        img = img.convert('RGB')

    # Try saving with decreasing quality until under max_bytes
    quality = 85
    while True:
        buf = BytesIO()
        img.save(buf, format='JPEG', quality=quality, optimize=True)
        size = buf.tell()
        if size <= max_bytes or quality <= 30:
            break
        quality -= 10

    _log(f"Final image size: {size} bytes (quality={quality})")
    return buf.getvalue()

def _upload_media(wp_url, auth, image_input, filename_hint="image.jpg"):
    _log(f"Uploading media, type={type(image_input)}")
    img_bytes = _image_to_jpeg_bytes(image_input, max_bytes=2_000_000)
    files = {'file': (filename_hint, img_bytes, 'image/jpeg')}
    resp = requests.post(f"{wp_url}/wp-json/wp/v2/media", files=files, auth=auth)
    if resp.status_code not in (200, 201):
        raise Exception(f"Media upload failed: {resp.status_code} - {resp.text}")
    data = resp.json()
    return data['id'], data['guid']['rendered']

def _get_category_ids(wp_url, auth, names):
    if not names:
        return []
    ids = []
    endpoint = f"{wp_url}/wp-json/wp/v2/categories"
    for name in names:
        resp = requests.get(endpoint, params={'search': name, 'per_page': 10}, auth=auth)
        if resp.status_code == 200:
            for cat in resp.json():
                if cat['name'].lower() == name.lower():
                    ids.append(cat['id'])
                    break
    return ids

def post(data: dict) -> dict:
    try:
        _log(f"Received data keys: {list(data.keys())}")
        wp = _load_config()
        wp_url = wp['url'].rstrip('/')
        auth = HTTPBasicAuth(wp['username'], wp['password'])
    except Exception as e:
        return {"status": "fail", "reason": f"Secrets error: {e}"}

    title = data.get("title", "Untitled")
    story = data.get("story", "")
    image_paths = data.get("image_paths", [])
    categories = data.get("categories", [])

    if not image_paths:
        return {"status": "fail", "reason": "No image"}

    first_input = image_paths[0]
    _log(f"first_input type: {type(first_input)}")

    try:
        # Determine filename for upload
        if isinstance(first_input, dict):
            filename = first_input.get('filename', 'image.jpg')
        else:
            filename = Path(first_input).name

        media_id, media_url = _upload_media(wp_url, auth, first_input, filename)
        cat_ids = _get_category_ids(wp_url, auth, categories)

        content = f"<p>{story}</p>"
        if media_url:
            content += f'\n<p><img src="{media_url}" alt="Post image" /></p>'

        resp = requests.post(
            f"{wp_url}/wp-json/wp/v2/posts",
            json={
                "title": title,
                "content": content,
                "status": "publish",
                "featured_media": media_id,
                "categories": cat_ids
            },
            auth=auth
        )
        if resp.status_code not in (200, 201):
            return {"status": "fail", "reason": f"Post creation failed: {resp.status_code} - {resp.text}"}
        _log("Post created successfully")
        return {"status": "success"}
    except Exception as e:
        _log(f"Error: {e}")
        return {"status": "fail", "reason": str(e)}
