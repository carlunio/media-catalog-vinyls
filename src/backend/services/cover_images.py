import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from ..config import COVERS_DIR, DISCOGS_USER_AGENT
from . import export, vinilos_raw

IMAGE_TIMEOUT_SECONDS = 30
DEFAULT_IMAGE_EXTENSION = ".jpg"
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


def _safe_cover_stem(item_id: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", str(item_id or "").strip()).strip("._")
    return stem or "cover"


def _existing_cover_path(item_id: str) -> Path | None:
    stem = _safe_cover_stem(item_id)
    for path in sorted(COVERS_DIR.glob(f"{stem}.*")):
        if path.is_file() and path.suffix.lower() in ALLOWED_IMAGE_EXTENSIONS:
            return path
    return None


def _extension_from_url(url: str) -> str | None:
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix == ".jpeg":
        return ".jpg"
    if suffix in ALLOWED_IMAGE_EXTENSIONS:
        return suffix
    return None


def _extension_from_content_type(content_type: str | None) -> str | None:
    media_type = str(content_type or "").split(";", 1)[0].strip().lower()
    return CONTENT_TYPE_EXTENSIONS.get(media_type)


def _download_cover(item_id: str, url: str) -> Path:
    headers = {"User-Agent": DISCOGS_USER_AGENT}
    response = requests.get(url, headers=headers, timeout=IMAGE_TIMEOUT_SECONDS)
    response.raise_for_status()

    content = bytes(response.content or b"")
    if not content:
        raise ValueError("La respuesta de imagen está vacía")

    extension = (
        _extension_from_content_type(response.headers.get("Content-Type"))
        or _extension_from_url(url)
        or DEFAULT_IMAGE_EXTENSION
    )
    COVERS_DIR.mkdir(parents=True, exist_ok=True)
    path = COVERS_DIR / f"{_safe_cover_stem(item_id)}{extension}"
    tmp_path = path.with_name(f"{path.name}.tmp")
    tmp_path.write_bytes(content)
    tmp_path.replace(path)
    return path


def download_cover_images(
    ids: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    preview = export.get_export_preview(ids=ids)
    selected_ids = list(preview["ids"])

    downloaded: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    missing: list[str] = []
    failed: list[dict[str, str]] = []

    for item_id in selected_ids:
        existing_path = _existing_cover_path(item_id)
        if existing_path is not None:
            skipped.append({"id": item_id, "path": str(existing_path)})
            continue

        image_url = vinilos_raw.get_primary_image_url(item_id)
        if not image_url:
            missing.append(item_id)
            continue

        try:
            cover_path = _download_cover(item_id, image_url)
        except Exception as exc:
            failed.append({"id": item_id, "url": image_url, "error": str(exc)})
            continue

        downloaded.append({"id": item_id, "path": str(cover_path), "url": image_url})

    return {
        "covers_dir": str(COVERS_DIR),
        "ids": selected_ids,
        "downloaded": downloaded,
        "skipped": skipped,
        "missing": missing,
        "failed": failed,
        "downloaded_count": len(downloaded),
        "skipped_count": len(skipped),
        "missing_count": len(missing),
        "failed_count": len(failed),
    }
