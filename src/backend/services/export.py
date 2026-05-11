import csv
from datetime import datetime
from pathlib import Path
from typing import Any

from ..config import EXPORTS_DIR
from ..database import get_connection
from . import vinilos


def query_export_rows() -> tuple[list[str], list[dict[str, Any]]]:
    with get_connection() as con:
        cur = con.execute(
            f'SELECT * FROM "{vinilos.EXPORT_VIEW_NAME}" ORDER BY "Ref. del artículo"'
        )
        columns = [desc[0] for desc in cur.description]
        tuples = cur.fetchall()

    rows = [dict(zip(columns, row)) for row in tuples]
    return columns, rows


def _serialize_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("\t", " ").replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\\n")


def get_export_preview() -> dict[str, Any]:
    columns, rows = query_export_rows()
    ids = [str(row.get("Ref. del artículo") or "").strip() for row in rows if str(row.get("Ref. del artículo") or "").strip()]
    return {
        "columns": columns,
        "rows": rows,
        "ids": ids,
        "rows_count": len(rows),
    }


def export_vinilos_txt(output_path: Path | None = None) -> dict[str, Any]:
    preview = get_export_preview()
    columns = preview["columns"]
    rows = preview["rows"]
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = EXPORTS_DIR / f"vinilos_{timestamp}.txt"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=columns,
            delimiter="\t",
            quoting=csv.QUOTE_MINIMAL,
            extrasaction="ignore",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({column: _serialize_value(row.get(column)) for column in columns})

    return {
        "path": output_path,
        "filename": output_path.name,
        "rows": len(rows),
        "columns": columns,
        "ids": preview["ids"],
    }


def mark_exported_items_as_uploaded(ids: list[str]) -> dict[str, Any]:
    normalized_ids = []
    for raw_id in ids:
        item_id = str(raw_id or "").strip()
        if item_id and item_id not in normalized_ids:
            normalized_ids.append(item_id)

    if not normalized_ids:
        return {"updated": 0, "ids": []}

    placeholders = ", ".join(["?"] * len(normalized_ids))
    eligible_statuses = ", ".join(["?"] * len(vinilos.EXPORTABLE_LISTING_STATUSES))
    params = normalized_ids + list(vinilos.EXPORTABLE_LISTING_STATUSES)

    with get_connection() as con:
        matched_rows = con.execute(
            f"""
            SELECT id
            FROM {vinilos.ITEMS_TABLE}
            WHERE id IN ({placeholders})
              AND listing_status IN ({eligible_statuses})
            """,
            params,
        ).fetchall()
        matched_ids = [str(row[0] or "").strip() for row in matched_rows if str(row[0] or "").strip()]
        if matched_ids:
            matched_placeholders = ", ".join(["?"] * len(matched_ids))
            con.execute(
                f"""
                UPDATE {vinilos.ITEMS_TABLE}
                SET listing_status = 'Subido', updated_at = CURRENT_TIMESTAMP
                WHERE id IN ({matched_placeholders})
                """,
                matched_ids,
            )

    return {
        "updated": len(matched_ids),
        "ids": matched_ids,
    }
