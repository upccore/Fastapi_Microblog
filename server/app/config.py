from pathlib import Path

BASE_DIR = Path("/app")
MEDIA_DIR = BASE_DIR / "media"
MEDIA_DIR.mkdir(exist_ok=True, parents=True)