from contextlib import closing
import json
from datetime import datetime

from ..database import get_connection
from ..normalizers import normalizar_año
from . import vinilos_raw


class ViniloNotFoundError(ValueError):
    pass


ITEMS_TABLE = "items"
EXPORT_VIEW_NAME = "export"
ALLOWED_VALUES_TABLE = "inventory_field_allowed_values"
EXPORTABLE_LISTING_STATUSES = ("Para subir", "Para actualizar")
EXPORT_VIEW_COLUMNS: list[tuple[str, str]] = [
    ("id", "Ref. del artículo"),
    ("product_type", "Tipo de artículo"),
    ("title", "Nombre"),
    ("artists", "Artista"),
    ("year", "Año"),
    ("labels", "Sello"),
    ("country", "País"),
    ("total_duration", "Duración"),
    ("estimated_weight", "Peso (g)"),
    ("genres", "Géneros"),
    ("styles", "Estilos"),
    ("media_condition", "Condición del disco"),
    ("sleeve_condition", "Condición de la funda"),
    ("condition_comments", "Comentarios sobre la conservación"),
    ("sale_price", "Precio (€)"),
    ("tracklist", "Tracklist"),
    ("notes", "Notas"),
]

API_TO_DB_FIELD = {
    "tipo_articulo": "product_type",
    "nombre": "title",
    "artista": "artists",
    "año": "year",
    "sello": "labels",
    "pais": "country",
    "duracion_total": "total_duration",
    "estimated_weight": "estimated_weight",
    "generos": "genres",
    "estilos": "styles",
    "estado_disco": "media_condition",
    "estado_funda": "sleeve_condition",
    "comentarios_estado": "condition_comments",
    "menor_precio": "lowest_price",
    "precio": "sale_price",
    "estado_carga": "listing_status",
    "estado_stock": "stock_status",
    "tracklist": "tracklist",
    "notas": "notes",
}
DB_TO_API_FIELD = {db_name: api_name for api_name, db_name in API_TO_DB_FIELD.items()}
API_OPTION_FIELDS = {
    "tipo_articulo",
    "estado_disco",
    "estado_funda",
    "estado_carga",
    "estado_stock",
}
OPTIONAL_TEXT_FIELDS = {
    "tipo_articulo",
    "nombre",
    "artista",
    "sello",
    "pais",
    "duracion_total",
    "generos",
    "estilos",
    "tracklist",
    "estado_disco",
    "estado_funda",
    "comentarios_estado",
    "estado_carga",
    "estado_stock",
    "notas",
}
INVENTORY_ALLOWED_VALUES: list[tuple[str, str]] = [
    ("product_type", "Vinilo"),
    ("product_type", "LP"),
    ("product_type", "EP"),
    ("product_type", "Single"),
    ("product_type", "Maxi single"),
    ("product_type", "CD"),
    ("product_type", "CD single"),
    ("product_type", "Cassette"),
    ("product_type", "DVD"),
    ("product_type", "Blu-ray"),
    ("product_type", "Box set"),
    ("media_condition", "M"),
    ("media_condition", "NM or M-"),
    ("media_condition", "VG+"),
    ("media_condition", "VG"),
    ("media_condition", "G+"),
    ("media_condition", "G"),
    ("media_condition", "F"),
    ("media_condition", "P"),
    ("sleeve_condition", "M"),
    ("sleeve_condition", "NM or M-"),
    ("sleeve_condition", "VG+"),
    ("sleeve_condition", "VG"),
    ("sleeve_condition", "G+"),
    ("sleeve_condition", "G"),
    ("sleeve_condition", "F"),
    ("sleeve_condition", "P"),
    ("sleeve_condition", "Not Graded"),
    ("sleeve_condition", "Generic"),
    ("sleeve_condition", "No Cover"),
    ("listing_status", "Para subir"),
    ("listing_status", "Para actualizar"),
    ("listing_status", "Subido"),
    ("stock_status", "En stock"),
    ("stock_status", "Vendido"),
    ("stock_status", "Extraviado"),
]
ITEM_DB_COLUMNS = [
    "id",
    "product_type",
    "title",
    "artists",
    "year",
    "labels",
    "country",
    "total_duration",
    "estimated_weight",
    "genres",
    "styles",
    "media_condition",
    "sleeve_condition",
    "condition_comments",
    "lowest_price",
    "sale_price",
    "listing_status",
    "stock_status",
    "tracklist",
    "notes",
    "updated_at",
]


def _join_names(items):
    names = []
    for item in items or []:
        name = str((item or {}).get("name") or "").strip()
        if name:
            names.append(name)
    return ", ".join(names)


def _join_label_names(data):
    return _join_names(data.get("labels", []) or [])


def _build_tracklist_text(data):
    tracklist = []
    for track in data.get("tracklist", []) or []:
        pos = str((track or {}).get("position") or "").strip()
        title = str((track or {}).get("title") or "").strip()
        duration = str((track or {}).get("duration") or "").strip()

        left = f"{pos} - {title}".strip(" -")
        if duration:
            left = f"{left} ({duration})"
        if left:
            tracklist.append(left)

    return "\n".join(tracklist)


def _parse_duration_to_seconds(value):
    text = str(value or "").strip()
    if not text:
        return None

    parts = text.split(":")
    if len(parts) == 2:
        minutes_text, seconds_text = parts
        if not minutes_text.isdigit() or not seconds_text.isdigit():
            return None
        minutes = int(minutes_text)
        seconds = int(seconds_text)
        if seconds >= 60:
            return None
        return minutes * 60 + seconds

    if len(parts) == 3:
        hours_text, minutes_text, seconds_text = parts
        if not hours_text.isdigit() or not minutes_text.isdigit() or not seconds_text.isdigit():
            return None
        hours = int(hours_text)
        minutes = int(minutes_text)
        seconds = int(seconds_text)
        if minutes >= 60 or seconds >= 60:
            return None
        return hours * 3600 + minutes * 60 + seconds

    return None


def _format_total_duration(total_seconds):
    hours, remainder = divmod(int(total_seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def _build_total_duration(data):
    total_seconds = 0
    has_duration = False

    for track in data.get("tracklist", []) or []:
        seconds = _parse_duration_to_seconds((track or {}).get("duration"))
        if seconds is None:
            continue
        total_seconds += seconds
        has_duration = True

    if not has_duration:
        return None

    return _format_total_duration(total_seconds)


def _clean_optional_text(value):
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _ensure_allowed_values_table(con) -> None:
    con.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {ALLOWED_VALUES_TABLE} (
            table_name TEXT,
            field_name TEXT,
            field_value TEXT,
            sort_order INTEGER DEFAULT 0,
            PRIMARY KEY (table_name, field_name, field_value)
        )
        """
    )
    con.execute(
        f"ALTER TABLE {ALLOWED_VALUES_TABLE} ADD COLUMN IF NOT EXISTS sort_order INTEGER DEFAULT 0"
    )


def _sync_allowed_values_table(con) -> None:
    _ensure_allowed_values_table(con)

    target_rows = [
        (ITEMS_TABLE, field_name, field_value, index)
        for index, (field_name, field_value) in enumerate(INVENTORY_ALLOWED_VALUES)
    ]
    target_keys = {(row[1], row[2]) for row in target_rows}

    current_rows = con.execute(
        f"""
        SELECT field_name, field_value, sort_order
        FROM {ALLOWED_VALUES_TABLE}
        WHERE table_name = ?
        """,
        (ITEMS_TABLE,),
    ).fetchall()
    current_map = {
        (str(row[0] or "").strip(), str(row[1] or "").strip()): int(row[2] or 0)
        for row in current_rows
        if str(row[0] or "").strip() and str(row[1] or "").strip()
    }

    insert_rows = [row for row in target_rows if (row[1], row[2]) not in current_map]
    if insert_rows:
        con.executemany(
            f"""
            INSERT INTO {ALLOWED_VALUES_TABLE} (table_name, field_name, field_value, sort_order)
            VALUES (?, ?, ?, ?)
            """,
            insert_rows,
        )

    update_rows = [
        (row[3], row[0], row[1], row[2])
        for row in target_rows
        if current_map.get((row[1], row[2])) is not None and current_map.get((row[1], row[2])) != row[3]
    ]
    if update_rows:
        con.executemany(
            f"""
            UPDATE {ALLOWED_VALUES_TABLE}
            SET sort_order = ?
            WHERE table_name = ? AND field_name = ? AND field_value = ?
            """,
            update_rows,
        )

    stale_rows = [
        (ITEMS_TABLE, field_name, field_value)
        for field_name, field_value in current_map
        if (field_name, field_value) not in target_keys
    ]
    if stale_rows:
        con.executemany(
            f"""
            DELETE FROM {ALLOWED_VALUES_TABLE}
            WHERE table_name = ? AND field_name = ? AND field_value = ?
            """,
            stale_rows,
        )


def _ensure_items_table(con) -> None:
    con.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {ITEMS_TABLE} (
            id TEXT PRIMARY KEY,
            product_type TEXT,
            title TEXT,
            artists TEXT,
            year INTEGER,
            labels TEXT,
            country TEXT,
            total_duration TEXT,
            estimated_weight REAL,
            genres TEXT,
            styles TEXT,
            media_condition TEXT,
            sleeve_condition TEXT,
            condition_comments TEXT,
            lowest_price REAL,
            sale_price REAL,
            listing_status TEXT,
            stock_status TEXT,
            tracklist TEXT,
            notes TEXT,
            updated_at TIMESTAMP
        )
        """
    )
    column_additions = [
        ("product_type", "TEXT"),
        ("title", "TEXT"),
        ("artists", "TEXT"),
        ("year", "INTEGER"),
        ("labels", "TEXT"),
        ("country", "TEXT"),
        ("total_duration", "TEXT"),
        ("estimated_weight", "REAL"),
        ("genres", "TEXT"),
        ("styles", "TEXT"),
        ("media_condition", "TEXT"),
        ("sleeve_condition", "TEXT"),
        ("condition_comments", "TEXT"),
        ("lowest_price", "REAL"),
        ("sale_price", "REAL"),
        ("listing_status", "TEXT"),
        ("stock_status", "TEXT"),
        ("tracklist", "TEXT"),
        ("notes", "TEXT"),
        ("updated_at", "TIMESTAMP"),
    ]
    for column_name, column_type in column_additions:
        con.execute(
            f"ALTER TABLE {ITEMS_TABLE} ADD COLUMN IF NOT EXISTS {column_name} {column_type}"
        )


def _quote_identifier(identifier: str) -> str:
    return '"' + str(identifier).replace('"', '""') + '"'


def _ensure_export_view(con) -> None:
    select_lines = [
        f"            {column_name} AS {_quote_identifier(column_label)}"
        for column_name, column_label in EXPORT_VIEW_COLUMNS
    ]
    select_sql = ",\n".join(select_lines)
    status_values = ", ".join(f"'{value}'" for value in EXPORTABLE_LISTING_STATUSES)
    con.execute(
        f"""
        CREATE OR REPLACE VIEW {_quote_identifier(EXPORT_VIEW_NAME)} AS
        SELECT
{select_sql}
        FROM {ITEMS_TABLE}
        WHERE listing_status IN ({status_values})
        """
    )


def _api_record_from_db_record(record: dict) -> dict:
    api_record = {"id": record.get("id")}
    for db_field, api_field in DB_TO_API_FIELD.items():
        api_record[api_field] = record.get(db_field)
    return api_record


def _db_update_payload_from_api_payload(data: dict) -> dict:
    normalized = dict(data)
    for field in OPTIONAL_TEXT_FIELDS:
        normalized[field] = _clean_optional_text(data.get(field))

    return {
        "product_type": normalized["tipo_articulo"],
        "title": normalized["nombre"],
        "artists": normalized["artista"],
        "year": normalizar_año(data.get("año")),
        "labels": normalized["sello"],
        "country": normalized["pais"],
        "total_duration": normalized["duracion_total"],
        "estimated_weight": data.get("estimated_weight"),
        "genres": normalized["generos"],
        "styles": normalized["estilos"],
        "tracklist": normalized["tracklist"],
        "media_condition": normalized["estado_disco"],
        "sleeve_condition": normalized.get("estado_funda"),
        "condition_comments": normalized["comentarios_estado"],
        "sale_price": data.get("precio"),
        "listing_status": normalized["estado_carga"],
        "stock_status": normalized["estado_stock"],
        "notes": normalized["notas"],
    }


def init_table():
    with closing(get_connection()) as con:
        _ensure_items_table(con)
        _sync_allowed_values_table(con)
        _ensure_export_view(con)


def preparar():
    with closing(get_connection()) as con:
        _ensure_items_table(con)
        raws = con.execute(
            f"""
            SELECT id, data
            FROM {vinilos_raw.RAW_TABLE_REF}
            WHERE id NOT IN (SELECT id FROM {ITEMS_TABLE})
            """
        ).fetchall()

        nuevos = 0
        for vid, raw_data in raws:
            data = json.loads(raw_data) if isinstance(raw_data, str) else raw_data

            con.execute(
                f"""
                INSERT INTO {ITEMS_TABLE} (
                    id, product_type, title, artists, year,
                    labels, country, total_duration, estimated_weight,
                    genres, styles, lowest_price,
                    listing_status, stock_status,
                    tracklist, notes, updated_at
                )
                VALUES (
                    ?, 'Vinilo', ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?,
                    'Para subir', 'En stock',
                    ?, ?, ?
                )
                """,
                (
                    vid,
                    data.get("title"),
                    _join_names(data.get("artists", [])),
                    normalizar_año(data.get("year")),
                    _join_label_names(data),
                    data.get("country"),
                    _build_total_duration(data),
                    data.get("estimated_weight"),
                    ", ".join(str(item).strip() for item in data.get("genres", []) if str(item).strip()),
                    ", ".join(str(item).strip() for item in data.get("styles", []) if str(item).strip()),
                    data.get("lowest_price"),
                    _build_tracklist_text(data),
                    data.get("notes"),
                    datetime.now(),
                ),
            )
            nuevos += 1

    return nuevos


def list_all():
    with closing(get_connection()) as con:
        rows = con.execute(
            f"""
            SELECT id, title
            FROM {ITEMS_TABLE}
            ORDER BY id
            """
        ).fetchall()

    return [{"id": row[0], "nombre": row[1]} for row in rows]


def get_one(id_):
    with closing(get_connection()) as con:
        row = con.execute(
            f"""
            SELECT {", ".join(ITEM_DB_COLUMNS[:-1])}
            FROM {ITEMS_TABLE}
            WHERE id = ?
            """,
            (id_,),
        ).fetchone()

    if not row:
        return None

    db_record = dict(zip(ITEM_DB_COLUMNS[:-1], row))
    api_record = _api_record_from_db_record(db_record)
    api_record["discogs_image_url"] = vinilos_raw.get_primary_image_url(id_)
    return api_record


def list_all_full():
    with closing(get_connection()) as con:
        rows = con.execute(
            f"""
            SELECT {", ".join(ITEM_DB_COLUMNS)}
            FROM {ITEMS_TABLE}
            ORDER BY title
            """
        ).fetchall()

    return [_api_record_from_db_record(dict(zip(ITEM_DB_COLUMNS, row))) for row in rows]


def update(id_, data: dict):
    payload = _db_update_payload_from_api_payload(data)

    with closing(get_connection()) as con:
        exists = con.execute(
            f"SELECT 1 FROM {ITEMS_TABLE} WHERE id = ? LIMIT 1",
            (id_,),
        ).fetchone()
        if not exists:
            raise ViniloNotFoundError(f"El vinilo {id_} no existe")

        con.execute(
            f"""
            UPDATE {ITEMS_TABLE}
            SET
                product_type = ?,
                title = ?,
                artists = ?,
                year = ?,
                labels = ?,
                country = ?,
                total_duration = ?,
                estimated_weight = ?,
                genres = ?,
                styles = ?,
                tracklist = ?,
                media_condition = ?,
                sleeve_condition = ?,
                condition_comments = ?,
                sale_price = ?,
                listing_status = ?,
                stock_status = ?,
                notes = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                payload["product_type"],
                payload["title"],
                payload["artists"],
                payload["year"],
                payload["labels"],
                payload["country"],
                payload["total_duration"],
                payload["estimated_weight"],
                payload["genres"],
                payload["styles"],
                payload["tracklist"],
                payload["media_condition"],
                payload["sleeve_condition"],
                payload["condition_comments"],
                payload["sale_price"],
                payload["listing_status"],
                payload["stock_status"],
                payload["notes"],
                datetime.now(),
                id_,
            ),
        )

    return get_one(id_)


def get_vinilos_allowed_values() -> dict[str, list[str]]:
    with closing(get_connection()) as con:
        rows = con.execute(
            f"""
            SELECT field_name, field_value
            FROM {ALLOWED_VALUES_TABLE}
            WHERE table_name = ?
            ORDER BY field_name, sort_order, field_value
            """,
            (ITEMS_TABLE,),
        ).fetchall()

    grouped: dict[str, list[str]] = {}
    for db_field_name, field_value in rows:
        db_name = str(db_field_name or "").strip()
        api_name = DB_TO_API_FIELD.get(db_name, db_name)
        value = str(field_value or "").strip()
        if api_name not in API_OPTION_FIELDS or not value:
            continue
        grouped.setdefault(api_name, [])
        if value not in grouped[api_name]:
            grouped[api_name].append(value)
    return grouped
