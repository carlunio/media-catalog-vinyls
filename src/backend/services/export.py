import csv
from datetime import datetime
from pathlib import Path
from typing import Any

from ..config import EXPORTS_DIR
from ..database import get_connection
from . import vinilos


def _normalize_ids(ids: list[str] | tuple[str, ...] | None) -> list[str]:
    normalized_ids: list[str] = []
    for raw_id in ids or []:
        item_id = str(raw_id or "").strip()
        if item_id and item_id not in normalized_ids:
            normalized_ids.append(item_id)
    return normalized_ids


def query_export_rows(ids: list[str] | tuple[str, ...] | None = None) -> tuple[list[str], list[dict[str, Any]]]:
    normalized_ids = _normalize_ids(ids)
    sql = f'SELECT * FROM "{vinilos.EXPORT_VIEW_NAME}"'
    params: list[Any] = []
    if normalized_ids:
        placeholders = ", ".join(["?"] * len(normalized_ids))
        sql += f' WHERE "{vinilos.EXPORT_REFERENCE_COLUMN}" IN ({placeholders})'
        params.extend(normalized_ids)
    sql += f' ORDER BY "{vinilos.EXPORT_REFERENCE_COLUMN}"'

    with get_connection() as con:
        cur = con.execute(sql, params)
        columns = [desc[0] for desc in cur.description]
        tuples = cur.fetchall()

    rows = [dict(zip(columns, row)) for row in tuples]
    return columns, rows


def _serialize_value(value: Any) -> str:
    if value is None:
        return ""
    return (
        str(value)
        .replace("#", " ")
        .replace('"', "'")
        .replace("\t", " ")
        .replace("\r\n", " / ")
        .replace("\r", " / ")
        .replace("\n", " / ")
    )


def get_export_preview(ids: list[str] | tuple[str, ...] | None = None) -> dict[str, Any]:
    columns, rows = query_export_rows(ids=ids)
    ids = [
        str(row.get(vinilos.EXPORT_REFERENCE_COLUMN) or "").strip()
        for row in rows
        if str(row.get(vinilos.EXPORT_REFERENCE_COLUMN) or "").strip()
    ]
    return {
        "columns": columns,
        "rows": rows,
        "ids": ids,
        "rows_count": len(rows),
    }


def export_vinilos_csv(
    output_path: Path | None = None,
    *,
    ids: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    preview = get_export_preview(ids=ids)
    columns = preview["columns"]
    rows = preview["rows"]
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = EXPORTS_DIR / f"vinilos_{timestamp}.csv"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=columns,
            delimiter="#",
            quoting=csv.QUOTE_NONE,
            extrasaction="ignore",
            lineterminator="\n",
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


def export_vinilos_txt(
    output_path: Path | None = None,
    *,
    ids: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    return export_vinilos_csv(output_path=output_path, ids=ids)


def clear_exported_items_listing_status(ids: list[str]) -> dict[str, Any]:
    normalized_ids = _normalize_ids(ids)

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
                SET listing_status = NULL, updated_at = CURRENT_TIMESTAMP
                WHERE id IN ({matched_placeholders})
                """,
                matched_ids,
            )

    return {
        "updated": len(matched_ids),
        "ids": matched_ids,
    }
