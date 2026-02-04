import os
from pathlib import Path

# -------------------------
# RUTA BASE DEL PROYECTO
# -------------------------
PROJECT_ROOT = Path(
    os.getenv("PROJECT_ROOT", Path.cwd())
)

# -------------------------
# BASE DE DATOS
# -------------------------
DB_PATH = Path(
    os.getenv(
        "DB_PATH",
        PROJECT_ROOT / "data" / "vinilos.duckdb"
    )
)

# -------------------------
# DISCOGS
# -------------------------
DISCOGS_TOKEN = os.environ.get("DISCOGS_TOKEN")
if not DISCOGS_TOKEN:
    raise RuntimeError("Falta la variable de entorno DISCOGS_TOKEN")


if __name__ == "__main__":
    print("PROJECT_ROOT:", PROJECT_ROOT)
    print("DB_PATH:", DB_PATH)
    print("DISCOGS_TOKEN:", "OK" if DISCOGS_TOKEN else "MISSING")
