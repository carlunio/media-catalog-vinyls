import csv
from contextlib import closing
import json
from datetime import datetime
import re

from ..config import IMPORTAMATIC_OTHERS_FIXED_COST_EXPORT, TC_SECTIONS_CSV_PATH
from ..database import get_connection
from ..normalizers import normalizar_año
from . import vinilos_raw


class ViniloNotFoundError(ValueError):
    pass


ITEMS_TABLE = "items"
EXPORT_VIEW_NAME = "export"
EXPORT_REFERENCE_COLUMN = "REFERENCIA"
ALLOWED_VALUES_TABLE = "inventory_field_allowed_values"
TC_SECTIONS_TABLE = "tc_sections"
EXPORTABLE_LISTING_STATUSES = ("ALTA", "CAMBIO", "BAJA")
TC_CONDITION_VALUES = ("5", "4", "3", "2", "1")
IMPORTAMATIC_EXPORT_COLUMNS = [
    "REFERENCIA",
    "TÍTULO",
    "DESCRIPCIÓN",
    "AUTOR ",
    "PRECIO",
    "OPERACIÓN",
    "SECCIÓN",
    "ESTADO",
    "DESCRIPCIÓN DEL ESTADO",
    "IMAGEN 1 (principal)",
    "IMAGEN 2",
    "IMAGEN 3",
    "FORMA DE ENVÍO",
    "GASTOS FIJOS",
]
TC_COMPACT_SECOND_LEVEL_PREFIXES = ("CD",)
TC_COMPOUND_SEGMENTS = (
    ("Pop", "Rock"),
    ("Punk", "Hard Core"),
    ("Reggae", "Ska"),
)
DISCOGS_FORMAT_NAME_TRANSLATIONS = {
    "Vinyl": "Vinilo",
    "Box Set": "Cofre",
}
LISTING_STATUS_MIGRATIONS = {
    "Para subir": "ALTA",
    "Para actualizar": "CAMBIO",
    "Subido": None,
    "alta": "ALTA",
    "cambio": "CAMBIO",
    "baja": "BAJA",
}

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
    "estado_tc": "tc_condition",
    "menor_precio": "lowest_price",
    "precio": "sale_price",
    "estado_carga": "listing_status",
    "estado_stock": "stock_status",
    "tracklist": "tracklist",
    "creditos": "credits",
    "notas": "notes",
    "tc_section": "tc_section",
}
DB_TO_API_FIELD = {db_name: api_name for api_name, db_name in API_TO_DB_FIELD.items()}
API_OPTION_FIELDS = {
    "estado_disco",
    "estado_funda",
    "estado_tc",
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
    "creditos",
    "estado_disco",
    "estado_funda",
    "comentarios_estado",
    "estado_tc",
    "estado_carga",
    "estado_stock",
    "notas",
}
INVENTORY_ALLOWED_VALUES: list[tuple[str, str]] = [
    ("media_condition", "M"),
    ("media_condition", "NM"),
    ("media_condition", "VG+"),
    ("media_condition", "VG"),
    ("media_condition", "G+"),
    ("media_condition", "G"),
    ("media_condition", "F"),
    ("sleeve_condition", "M"),
    ("sleeve_condition", "NM"),
    ("sleeve_condition", "VG+"),
    ("sleeve_condition", "VG"),
    ("sleeve_condition", "G+"),
    ("sleeve_condition", "G"),
    ("sleeve_condition", "F"),
    ("sleeve_condition", "Not Graded"),
    ("sleeve_condition", "Generic"),
    ("sleeve_condition", "No Cover"),
    *[("tc_condition", value) for value in TC_CONDITION_VALUES],
    *[("listing_status", value) for value in EXPORTABLE_LISTING_STATUSES],
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
    "tc_condition",
    "lowest_price",
    "sale_price",
    "listing_status",
    "stock_status",
    "tracklist",
    "credits",
    "notes",
    "tc_section",
    "updated_at",
]
LEGACY_PRODUCT_TYPES = {
    "Vinilo",
    "LP",
    "EP",
    "Single",
    "Maxi single",
    "CD",
    "CD single",
    "Cassette",
    "DVD",
    "Blu-ray",
    "Box set",
}


def _join_names(items):
    names = []
    for item in items or []:
        name = str((item or {}).get("name") or "").strip()
        if name:
            names.append(name)
    return ", ".join(names)


def _join_label_names(data):
    return _join_names(data.get("labels", []) or [])


def _clean_discogs_person_name(value):
    text = _clean_optional_text(value)
    if not text:
        return None
    return re.sub(r"\s+\(\d+\)$", "", text).strip() or None


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


def _build_credits_text(data):
    if not isinstance(data, dict):
        return None

    credits = []
    for item in data.get("extraartists", []) or []:
        if not isinstance(item, dict):
            continue

        role = _clean_optional_text(item.get("role"))
        artist_name = _clean_discogs_person_name(item.get("anv")) or _clean_discogs_person_name(
            item.get("name")
        )
        if not role or not artist_name:
            continue

        tracks = _clean_optional_text(item.get("tracks"))
        left = role if not tracks else f"{role} [{tracks}]"
        credits.append(f"{left} – {artist_name}")

    return "\n".join(credits)


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


def _clean_sql_text(expression: str) -> str:
    return (
        "NULLIF(TRIM(REGEXP_REPLACE("
        f"CAST({expression} AS VARCHAR), '[\\r\\n\\t]+', ' / ', 'g'"
        ")), '')"
    )


def _labeled_sql_part(label: str, expression: str) -> str:
    clean_expression = _clean_sql_text(expression)
    escaped_label = label.replace("'", "''")
    return f"CASE WHEN {clean_expression} IS NOT NULL THEN '{escaped_label}: ' || {clean_expression} END"


def _tc_condition_description_sql() -> str:
    description = (
        "CONCAT_WS('. ', "
        f"{_labeled_sql_part('Disco', 'item.media_condition')}, "
        f"{_labeled_sql_part('Funda', 'item.sleeve_condition')}, "
        f"{_clean_sql_text('item.condition_comments')}"
        ")"
    )
    return (
        f"CASE "
        f"WHEN NULLIF({description}, '') IS NULL THEN NULL "
        f"WHEN REGEXP_MATCHES({description}, '[.!?]$') THEN {description} "
        f"ELSE {description} || '.' END"
    )


def _html_clean_sql_text(expression: str, *, preserve_line_breaks: bool = False) -> str:
    normalized_tabs = f"REGEXP_REPLACE(CAST({expression} AS VARCHAR), '[\\t]+', ' ', 'g')"
    if preserve_line_breaks:
        normalized_text = (
            f"REPLACE(REPLACE({normalized_tabs}, CHR(13) || CHR(10), CHR(10)), "
            "CHR(13), CHR(10))"
        )
    else:
        normalized_text = f"REGEXP_REPLACE({normalized_tabs}, '[\\r\\n]+', ' / ', 'g')"
    return f"NULLIF(TRIM({normalized_text}), '')"


def _html_escape_sql(expression: str, *, preserve_line_breaks: bool = False) -> str:
    clean_expression = _html_clean_sql_text(expression, preserve_line_breaks=preserve_line_breaks)
    return (
        "REPLACE(REPLACE(REPLACE("
        f"{clean_expression}, "
        "'&', '&amp;'), '<', '&lt;'), '>', '&gt;')"
    )


def _html_paragraph_sql(label: str, expression: str, *, preserve_line_breaks: bool = False) -> str:
    escaped_label = label.replace("'", "''")
    clean_expression = _html_escape_sql(expression, preserve_line_breaks=preserve_line_breaks)
    content_expression = (
        f"REPLACE(REPLACE({clean_expression}, CHR(10) || CHR(10), '<br><br>'), CHR(10), '<br>')"
        if preserve_line_breaks
        else clean_expression
    )
    return (
        f"CASE WHEN {clean_expression} IS NOT NULL "
        f"THEN '<p><strong>{escaped_label}:</strong> ' || {content_expression} || '</p>' END"
    )


def _html_list_sql(label: str, expression: str) -> str:
    escaped_label = label.replace("'", "''")
    clean_expression = _html_escape_sql(expression, preserve_line_breaks=True)
    list_items_expression = f"REPLACE({clean_expression}, CHR(10), '</li><li>')"
    return (
        f"CASE WHEN {clean_expression} IS NOT NULL "
        f"THEN '<p><strong>{escaped_label}:</strong></p><ul><li>' "
        f"|| {list_items_expression} || '</li></ul>' END"
    )


def _html_block_paragraph_sql(label: str, expression: str) -> str:
    escaped_label = label.replace("'", "''")
    clean_expression = _html_escape_sql(expression, preserve_line_breaks=True)
    content_expression = (
        f"REPLACE(REPLACE({clean_expression}, CHR(10) || CHR(10), '<br><br>'), CHR(10), '<br>')"
    )
    return (
        f"CASE WHEN {clean_expression} IS NOT NULL "
        f"THEN '<p><strong>{escaped_label}:</strong></p><p>' || {content_expression} || '</p>' END"
    )


def _tc_description_sql() -> str:
    description = (
        "CONCAT_WS('', "
        f"{_html_paragraph_sql('Formato', 'item.product_type')}, "
        f"{_html_paragraph_sql('Año', 'item.year')}, "
        f"{_html_paragraph_sql('Sello', 'item.labels')}, "
        f"{_html_paragraph_sql('País', 'item.country')}, "
        f"{_html_paragraph_sql('Duración', 'item.total_duration')}, "
        f"{_html_paragraph_sql('Géneros', 'item.genres')}, "
        f"{_html_paragraph_sql('Estilos', 'item.styles')}, "
        f"{_html_paragraph_sql('Comentarios de conservación', 'item.condition_comments', preserve_line_breaks=True)}, "
        f"{_html_list_sql('Tracklist', 'item.tracklist')}, "
        f"{_html_list_sql('Créditos', 'item.credits')}, "
        f"{_html_block_paragraph_sql('Notas', 'item.notes')}"
        ")"
    )
    fallback = f"'<p>' || {_html_escape_sql('item.title')} || '</p>'"
    return f"COALESCE(NULLIF({description}, ''), {fallback}, '')"


def _translate_discogs_format_name(name):
    clean_name = _clean_optional_text(name)
    if not clean_name:
        return None
    return DISCOGS_FORMAT_NAME_TRANSLATIONS.get(clean_name, clean_name)


def _parse_discogs_format_qty(value):
    clean_value = _clean_optional_text(value)
    if not clean_value:
        return None
    try:
        qty = int(clean_value)
    except ValueError:
        return None
    return qty if qty > 0 else None


def _build_product_type_from_formats(data):
    if not isinstance(data, dict):
        return None

    formatted_items = []
    for raw_format in data.get("formats", []) or []:
        if not isinstance(raw_format, dict):
            continue

        translated_name = _translate_discogs_format_name(raw_format.get("name"))
        if not translated_name:
            continue

        qty = _parse_discogs_format_qty(raw_format.get("qty"))
        parts = [f"{qty} x {translated_name}" if qty and qty > 1 else translated_name]

        for description in raw_format.get("descriptions", []) or []:
            clean_description = _clean_optional_text(description)
            if clean_description:
                parts.append(clean_description)

        extra_text = _clean_optional_text(raw_format.get("text"))
        if extra_text:
            parts.append(extra_text)

        formatted_items.append(", ".join(parts))

    return "; ".join(formatted_items) or None


def _normalize_tc_section_value(value):
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else None

    text = str(value).strip()
    if not text or text.lower() in {"none", "null", "nan"}:
        return None

    return text


def _table_column_names(con, table_name):
    rows = con.execute(f"PRAGMA table_info('{table_name}')").fetchall()
    return [str(row[1] or "").strip() for row in rows if str(row[1] or "").strip()]


def _tc_node_key(path_labels):
    return json.dumps(list(path_labels), ensure_ascii=False)


def _normalize_tc_title_parts(title: str) -> list[str]:
    raw_parts = [part.strip() for part in str(title or "").split(" - ") if part.strip()]
    if not raw_parts:
        return []

    expanded_parts: list[str] = []
    for index, part in enumerate(raw_parts):
        if index == 1:
            matched_prefix = False
            for prefix in TC_COMPACT_SECOND_LEVEL_PREFIXES:
                marker = f"{prefix} "
                if part.startswith(marker):
                    expanded_parts.append(prefix)
                    remainder = part[len(marker) :].strip()
                    if remainder:
                        expanded_parts.append(remainder)
                    matched_prefix = True
                    break
            if matched_prefix:
                continue
        expanded_parts.append(part)

    normalized_parts: list[str] = []
    index = 0
    while index < len(expanded_parts):
        current = expanded_parts[index]
        next_part = expanded_parts[index + 1] if index + 1 < len(expanded_parts) else None

        merged = False
        if next_part:
            for prefix, compound in TC_COMPOUND_SEGMENTS:
                if current != prefix:
                    continue
                if next_part == compound:
                    normalized_parts.append(f"{prefix} - {compound}")
                    index += 2
                    merged = True
                    break

                marker = f"{compound} "
                if next_part.startswith(marker):
                    normalized_parts.append(f"{prefix} - {compound}")
                    remainder = next_part[len(marker) :].strip()
                    if remainder:
                        normalized_parts.append(remainder)
                    index += 2
                    merged = True
                    break

        if merged:
            continue

        normalized_parts.append(current)
        index += 1

    return normalized_parts


def _build_tc_section_nodes() -> list[dict]:
    if not TC_SECTIONS_CSV_PATH.exists():
        return []

    nodes_by_key: dict[str, dict] = {}
    next_sort_order_by_parent: dict[str | None, int] = {}

    with TC_SECTIONS_CSV_PATH.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            section_id = _normalize_tc_section_value(row.get("id sección"))
            title = _clean_optional_text(row.get("título"))
            path_labels = _normalize_tc_title_parts(title or "")
            if section_id is None or not path_labels:
                continue

            path_keys: list[str] = []
            for depth in range(1, len(path_labels) + 1):
                node_path = tuple(path_labels[:depth])
                node_key = _tc_node_key(node_path)
                path_keys.append(node_key)
                if node_key in nodes_by_key:
                    continue

                parent_key = path_keys[-2] if len(path_keys) > 1 else None
                sort_order = next_sort_order_by_parent.get(parent_key, 0)
                next_sort_order_by_parent[parent_key] = sort_order + 1
                display_path = " > ".join(path_labels[1:depth]) or path_labels[0]
                nodes_by_key[node_key] = {
                    "node_key": node_key,
                    "parent_key": parent_key,
                    "section_id": None,
                    "label": path_labels[depth - 1],
                    "depth": depth - 1,
                    "path_labels": list(path_labels[:depth]),
                    "path_keys": list(path_keys),
                    "path_text": " > ".join(path_labels[:depth]),
                    "display_path": display_path,
                    "is_leaf": False,
                    "sort_order": sort_order,
                }

            leaf_node = nodes_by_key[path_keys[-1]]
            leaf_node["section_id"] = section_id
            leaf_node["is_leaf"] = True

    return sorted(
        nodes_by_key.values(),
        key=lambda node: (int(node["depth"]), int(node["sort_order"]), str(node["path_text"])),
    )


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
            tc_condition TEXT,
            lowest_price REAL,
            sale_price REAL,
            listing_status TEXT,
            stock_status TEXT,
            tracklist TEXT,
            credits TEXT,
            notes TEXT,
            tc_section TEXT,
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
        ("tc_condition", "TEXT"),
        ("lowest_price", "REAL"),
        ("sale_price", "REAL"),
        ("listing_status", "TEXT"),
        ("stock_status", "TEXT"),
        ("tracklist", "TEXT"),
        ("credits", "TEXT"),
        ("notes", "TEXT"),
        ("tc_section", "TEXT"),
        ("updated_at", "TIMESTAMP"),
    ]
    for column_name, column_type in column_additions:
        con.execute(
            f"ALTER TABLE {ITEMS_TABLE} ADD COLUMN IF NOT EXISTS {column_name} {column_type}"
        )
    con.execute(f"ALTER TABLE {ITEMS_TABLE} ALTER COLUMN tc_section TYPE TEXT")


def _sync_product_types_from_raw(con) -> None:
    item_columns = set(_table_column_names(con, ITEMS_TABLE))
    if "product_type" not in item_columns:
        return

    rows = con.execute(
        f"""
        SELECT i.id, i.product_type, r.data
        FROM {ITEMS_TABLE} AS i
        LEFT JOIN {vinilos_raw.RAW_TABLE_REF} AS r ON r.id = i.id
        ORDER BY i.id
        """
    ).fetchall()

    update_rows = []
    for item_id, current_product_type, raw_data in rows:
        current_value = _clean_optional_text(current_product_type)
        raw_payload = json.loads(raw_data) if isinstance(raw_data, str) else raw_data
        derived_value = _build_product_type_from_formats(raw_payload)

        if not derived_value:
            continue
        if current_value and current_value not in LEGACY_PRODUCT_TYPES:
            continue
        if current_value == derived_value:
            continue
        update_rows.append((derived_value, item_id))

    if update_rows:
        con.executemany(
            f"""
            UPDATE {ITEMS_TABLE}
            SET product_type = ?
            WHERE id = ?
            """,
            update_rows,
        )


def _sync_credits_from_raw(con) -> None:
    rows = con.execute(
        f"""
        SELECT i.id, i.credits, r.data
        FROM {ITEMS_TABLE} AS i
        LEFT JOIN {vinilos_raw.RAW_TABLE_REF} AS r ON r.id = i.id
        ORDER BY i.id
        """
    ).fetchall()

    update_rows = []
    for item_id, current_credits, raw_data in rows:
        current_value = _clean_optional_text(current_credits)
        raw_payload = json.loads(raw_data) if isinstance(raw_data, str) else raw_data
        derived_value = _build_credits_text(raw_payload)

        if not derived_value or current_value == derived_value:
            continue
        if current_value:
            continue
        update_rows.append((derived_value, item_id))

    if update_rows:
        con.executemany(
            f"""
            UPDATE {ITEMS_TABLE}
            SET credits = ?
            WHERE id = ?
            """,
            update_rows,
        )


def _ensure_tc_sections_table(con) -> None:
    con.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {TC_SECTIONS_TABLE} (
            node_key TEXT PRIMARY KEY,
            parent_key TEXT,
            section_id TEXT,
            label TEXT NOT NULL,
            depth INTEGER NOT NULL,
            path_labels VARCHAR[],
            path_keys VARCHAR[],
            path_text TEXT NOT NULL,
            display_path TEXT NOT NULL,
            is_leaf BOOLEAN NOT NULL,
            sort_order INTEGER DEFAULT 0
        )
        """
    )
    column_additions = [
        ("parent_key", "TEXT"),
        ("section_id", "TEXT"),
        ("label", "TEXT"),
        ("depth", "INTEGER"),
        ("path_labels", "VARCHAR[]"),
        ("path_keys", "VARCHAR[]"),
        ("path_text", "TEXT"),
        ("display_path", "TEXT"),
        ("is_leaf", "BOOLEAN"),
        ("sort_order", "INTEGER DEFAULT 0"),
    ]
    for column_name, column_type in column_additions:
        con.execute(
            f"ALTER TABLE {TC_SECTIONS_TABLE} ADD COLUMN IF NOT EXISTS {column_name} {column_type}"
        )
    con.execute(f"ALTER TABLE {TC_SECTIONS_TABLE} ALTER COLUMN section_id TYPE TEXT")


def _sync_tc_sections_table(con) -> None:
    _ensure_tc_sections_table(con)
    rows = _build_tc_section_nodes()
    con.execute(f"DELETE FROM {TC_SECTIONS_TABLE}")
    if not rows:
        return

    con.executemany(
        f"""
        INSERT INTO {TC_SECTIONS_TABLE} (
            node_key,
            parent_key,
            section_id,
            label,
            depth,
            path_labels,
            path_keys,
            path_text,
            display_path,
            is_leaf,
            sort_order
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["node_key"],
                row["parent_key"],
                row["section_id"],
                row["label"],
                row["depth"],
                row["path_labels"],
                row["path_keys"],
                row["path_text"],
                row["display_path"],
                row["is_leaf"],
                row["sort_order"],
            )
            for row in rows
        ],
    )


def _sync_listing_status_values(con) -> None:
    for legacy_value, target_value in LISTING_STATUS_MIGRATIONS.items():
        con.execute(
            f"""
            UPDATE {ITEMS_TABLE}
            SET listing_status = ?
            WHERE listing_status = ?
            """,
            (target_value, legacy_value),
        )


def _sync_condition_values(con) -> None:
    condition_migrations = {
        "NM or M-": "NM",
        "P": "F",
    }
    for field_name in ("media_condition", "sleeve_condition"):
        for legacy_value, target_value in condition_migrations.items():
            con.execute(
                f"""
                UPDATE {ITEMS_TABLE}
                SET {field_name} = ?
                WHERE {field_name} = ?
                """,
                (target_value, legacy_value),
            )


def _quote_identifier(identifier: str) -> str:
    return '"' + str(identifier).replace('"', '""') + '"'


def _ensure_export_view(con) -> None:
    price_sql = "REPLACE(CAST(item.sale_price AS VARCHAR), '.', ',')"
    select_expression_by_column = {
        EXPORT_REFERENCE_COLUMN: "item.id",
        "TÍTULO": "LEFT(item.title, 100)",
        "DESCRIPCIÓN": _tc_description_sql(),
        "AUTOR ": "LEFT(item.artists, 100)",
        "PRECIO": price_sql,
        "OPERACIÓN": "item.listing_status",
        "SECCIÓN": "item.tc_section",
        "ESTADO": "item.tc_condition",
        "DESCRIPCIÓN DEL ESTADO": f"LEFT({_tc_condition_description_sql()}, 100)",
        "IMAGEN 1 (principal)": "NULL",
        "IMAGEN 2": "NULL",
        "IMAGEN 3": "NULL",
        "FORMA DE ENVÍO": "'Otros'",
        "GASTOS FIJOS": f"'{IMPORTAMATIC_OTHERS_FIXED_COST_EXPORT}'",
    }
    select_lines = [
        f"            {select_expression_by_column[column_label]} AS {_quote_identifier(column_label)}"
        for column_label in IMPORTAMATIC_EXPORT_COLUMNS
    ]
    select_sql = ",\n".join(select_lines)
    status_values = ", ".join(f"'{value}'" for value in EXPORTABLE_LISTING_STATUSES)
    con.execute(
        f"""
        CREATE OR REPLACE VIEW {_quote_identifier(EXPORT_VIEW_NAME)} AS
        SELECT
{select_sql}
        FROM {ITEMS_TABLE} AS item
        LEFT JOIN {vinilos_raw.RAW_TABLE_REF} AS raw ON raw.id = item.id
        WHERE item.listing_status IN ({status_values})
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
        "credits": normalized["creditos"],
        "media_condition": normalized["estado_disco"],
        "sleeve_condition": normalized.get("estado_funda"),
        "condition_comments": normalized["comentarios_estado"],
        "tc_condition": normalized["estado_tc"],
        "sale_price": data.get("precio"),
        "listing_status": normalized["estado_carga"],
        "stock_status": normalized["estado_stock"],
        "notes": normalized["notas"],
        "tc_section": _normalize_tc_section_value(data.get("tc_section")),
    }


def init_table():
    with closing(get_connection()) as con:
        _ensure_items_table(con)
        _sync_listing_status_values(con)
        _sync_condition_values(con)
        _sync_product_types_from_raw(con)
        _sync_credits_from_raw(con)
        _sync_allowed_values_table(con)
        _sync_tc_sections_table(con)
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
                    tracklist, credits, notes, updated_at
                )
                VALUES (
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?,
                    'ALTA', 'En stock',
                    ?, ?, ?, ?
                )
                """,
                (
                    vid,
                    _build_product_type_from_formats(data),
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
                    _build_credits_text(data),
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
                credits = ?,
                media_condition = ?,
                sleeve_condition = ?,
                condition_comments = ?,
                tc_condition = ?,
                sale_price = ?,
                listing_status = ?,
                stock_status = ?,
                tc_section = ?,
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
                payload["credits"],
                payload["media_condition"],
                payload["sleeve_condition"],
                payload["condition_comments"],
                payload["tc_condition"],
                payload["sale_price"],
                payload["listing_status"],
                payload["stock_status"],
                payload["tc_section"],
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


def get_tc_sections_catalog() -> dict[str, object]:
    with closing(get_connection()) as con:
        rows = con.execute(
            f"""
            SELECT
                node_key,
                parent_key,
                section_id,
                label,
                depth,
                path_labels,
                path_keys,
                path_text,
                display_path,
                is_leaf,
                sort_order
            FROM {TC_SECTIONS_TABLE}
            ORDER BY depth, sort_order, path_text
            """
        ).fetchall()

    nodes = [
        {
            "node_key": row[0],
            "parent_key": row[1],
            "section_id": row[2],
            "label": row[3],
            "depth": int(row[4] or 0),
            "path_labels": list(row[5] or []),
            "path_keys": list(row[6] or []),
            "path_text": row[7],
            "display_path": row[8],
            "is_leaf": bool(row[9]),
            "sort_order": int(row[10] or 0),
        }
        for row in rows
    ]
    root_key = next((node["node_key"] for node in nodes if int(node["depth"]) == 0), None)
    return {"root_key": root_key, "nodes": nodes}
