import os
from pathlib import Path

PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT", Path.cwd())).resolve()


def _resolve_path(env_name: str, default_relative: str) -> Path:
    raw = os.getenv(env_name, default_relative)
    path = Path(raw)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


DB_PATH = _resolve_path("DB_PATH", "data/vinilos.duckdb")
EXPORTS_DIR = _resolve_path("EXPORTS_DIR", "data/exports")

DISCOGS_TOKEN = os.environ.get("DISCOGS_TOKEN")
DISCOGS_USER_AGENT = os.getenv("DISCOGS_USER_AGENT", "MediaCatalogVinyls/0.1")


if __name__ == "__main__":
    print("PROJECT_ROOT:", PROJECT_ROOT)
    print("DB_PATH:", DB_PATH)
    print("EXPORTS_DIR:", EXPORTS_DIR)
    print("DISCOGS_TOKEN:", "OK" if DISCOGS_TOKEN else "MISSING")
