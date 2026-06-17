import os
import socket
from decimal import Decimal, InvalidOperation
from pathlib import Path

PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT", Path.cwd())).resolve()


def _resolve_path(env_name: str, default_relative: str) -> Path:
    raw = os.getenv(env_name, default_relative)
    path = Path(raw)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def _parse_decimal_setting(env_name: str, default_value: str) -> Decimal:
    raw_value = str(os.getenv(env_name, default_value)).strip()
    normalized_value = raw_value.replace(",", ".")
    try:
        parsed_value = Decimal(normalized_value)
    except InvalidOperation as exc:
        raise ValueError(f"{env_name} must be a decimal number, got {raw_value!r}") from exc
    if parsed_value < 0:
        raise ValueError(f"{env_name} must be zero or positive, got {raw_value!r}")
    return parsed_value


def _format_decimal_for_export(value: Decimal) -> str:
    text = format(value.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _parse_int_setting(env_name: str, default_value: str, *, minimum: int) -> int:
    raw_value = str(os.getenv(env_name, default_value)).strip()
    try:
        parsed_value = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{env_name} must be an integer, got {raw_value!r}") from exc
    if parsed_value < minimum:
        raise ValueError(f"{env_name} must be at least {minimum}, got {raw_value!r}")
    return parsed_value


DB_SCHEMA = os.getenv("DB_SCHEMA", "main").strip() or "main"
DB_PATH = _resolve_path("DB_PATH", "data/vinyls.duckdb")
EXPORTS_DIR = _resolve_path("EXPORTS_DIR", "data/exports")
TC_SECTIONS_CSV_PATH = _resolve_path("TC_SECTIONS_CSV_PATH", "data/secciones.csv")
CLOUD_SNAPSHOTS_DIR = _resolve_path("CLOUD_SNAPSHOTS_DIR", "../bbdd/media-catalog-vinyls")
SYNC_STATE_PATH = _resolve_path("SYNC_STATE_PATH", "data/sync_state.json")
SYNC_ACTOR = os.getenv("SYNC_ACTOR", os.getenv("USER", "usuario")).strip() or "usuario"
SYNC_DEVICE = os.getenv("SYNC_DEVICE", socket.gethostname()).strip() or "equipo"
SYNC_RETENTION_DAYS = _parse_int_setting("SYNC_RETENTION_DAYS", "14", minimum=0)
SYNC_KEEP_MIN = _parse_int_setting("SYNC_KEEP_MIN", "10", minimum=1)
IMPORTAMATIC_OTHERS_FIXED_COST = _parse_decimal_setting(
    "IMPORTAMATIC_OTHERS_FIXED_COST",
    "4.5",
)
IMPORTAMATIC_OTHERS_FIXED_COST_EXPORT = _format_decimal_for_export(
    IMPORTAMATIC_OTHERS_FIXED_COST
).replace(".", ",")

DISCOGS_TOKEN = os.environ.get("DISCOGS_TOKEN")
DISCOGS_USER_AGENT = os.getenv("DISCOGS_USER_AGENT", "MediaCatalogVinyls/0.1")


if __name__ == "__main__":
    print("PROJECT_ROOT:", PROJECT_ROOT)
    print("DB_SCHEMA:", DB_SCHEMA)
    print("DB_PATH:", DB_PATH)
    print("EXPORTS_DIR:", EXPORTS_DIR)
    print("TC_SECTIONS_CSV_PATH:", TC_SECTIONS_CSV_PATH)
    print("CLOUD_SNAPSHOTS_DIR:", CLOUD_SNAPSHOTS_DIR)
    print("SYNC_STATE_PATH:", SYNC_STATE_PATH)
    print("SYNC_ACTOR:", SYNC_ACTOR)
    print("SYNC_DEVICE:", SYNC_DEVICE)
    print("SYNC_RETENTION_DAYS:", SYNC_RETENTION_DAYS)
    print("SYNC_KEEP_MIN:", SYNC_KEEP_MIN)
    print("IMPORTAMATIC_OTHERS_FIXED_COST:", IMPORTAMATIC_OTHERS_FIXED_COST_EXPORT)
    print("DISCOGS_TOKEN:", "OK" if DISCOGS_TOKEN else "MISSING")
