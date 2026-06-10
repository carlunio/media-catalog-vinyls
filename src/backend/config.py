import os
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


DB_SCHEMA = os.getenv("DB_SCHEMA", "main").strip() or "main"
DB_PATH = _resolve_path("DB_PATH", "data/vinyls.duckdb")
EXPORTS_DIR = _resolve_path("EXPORTS_DIR", "data/exports")
TC_SECTIONS_CSV_PATH = _resolve_path("TC_SECTIONS_CSV_PATH", "data/secciones.csv")
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
    print("IMPORTAMATIC_OTHERS_FIXED_COST:", IMPORTAMATIC_OTHERS_FIXED_COST_EXPORT)
    print("DISCOGS_TOKEN:", "OK" if DISCOGS_TOKEN else "MISSING")
