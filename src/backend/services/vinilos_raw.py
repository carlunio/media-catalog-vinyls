from contextlib import closing
import json

from ..database import get_connection


class DuplicateViniloRawError(ValueError):
    pass


RAW_TABLE = "discogs_release_payloads"
LEGACY_RAW_TABLE = "vinilos_raw"


def _load_raw_json(value):
    if isinstance(value, str):
        return json.loads(value)
    return value


def _join_names(items):
    names = []
    for item in items or []:
        name = str((item or {}).get("name") or "").strip()
        if name:
            names.append(name)
    return ", ".join(names)


def _table_exists(con, table_name):
    rows = con.execute("PRAGMA show_tables").fetchall()
    return table_name in {str(row[0] or "").strip() for row in rows}


def _table_columns(con, table_name):
    rows = con.execute(f"PRAGMA table_info('{table_name}')").fetchall()
    return {
        str(row[1] or "").strip(): str(row[2] or "").strip().upper()
        for row in rows
        if str(row[1] or "").strip()
    }


def _drop_legacy_raw_json_column(con, table_name):
    columns = _table_columns(con, table_name)
    if "raw_json" not in columns:
        return

    con.execute(
        f"""
        UPDATE {table_name}
        SET data = CASE
            WHEN raw_json IS NULL THEN NULL
            ELSE CAST(CAST(raw_json AS VARCHAR) AS JSON)
        END
        WHERE data IS NULL
        """
    )

    try:
        con.execute(f"ALTER TABLE {table_name} DROP COLUMN raw_json")
        return
    except Exception:
        pass

    inserted_at_sql = "inserted_at" if "inserted_at" in columns else "now()"
    rebuilt_table = f"{table_name}_rebuilt"
    con.execute(
        f"""
        CREATE TABLE {rebuilt_table} (
            id TEXT PRIMARY KEY,
            data JSON,
            inserted_at TIMESTAMP DEFAULT now()
        )
        """
    )
    con.execute(
        f"""
        INSERT INTO {rebuilt_table} (id, data, inserted_at)
        SELECT id, data, {inserted_at_sql}
        FROM {table_name}
        """
    )
    con.execute(f"DROP TABLE {table_name}")
    con.execute(f"ALTER TABLE {rebuilt_table} RENAME TO {table_name}")


def _migrate_legacy_raw_table(con):
    if not _table_exists(con, LEGACY_RAW_TABLE):
        return

    if not _table_exists(con, RAW_TABLE):
        con.execute(f"ALTER TABLE {LEGACY_RAW_TABLE} RENAME TO {RAW_TABLE}")
        return

    legacy_columns = _table_columns(con, LEGACY_RAW_TABLE)
    raw_value_expression = (
        "CAST(CAST(raw_json AS VARCHAR) AS JSON)"
        if "raw_json" in legacy_columns and "data" not in legacy_columns
        else "data"
    )
    inserted_at_expression = "inserted_at" if "inserted_at" in legacy_columns else "now()"
    con.execute(
        f"""
        INSERT INTO {RAW_TABLE} (id, data, inserted_at)
        SELECT id, {raw_value_expression}, {inserted_at_expression}
        FROM {LEGACY_RAW_TABLE}
        WHERE id NOT IN (SELECT id FROM {RAW_TABLE})
        """
    )
    con.execute(f"DROP TABLE {LEGACY_RAW_TABLE}")


def _ensure_schema(con):
    _migrate_legacy_raw_table(con)
    con.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {RAW_TABLE} (
            id TEXT PRIMARY KEY,
            data JSON,
            inserted_at TIMESTAMP DEFAULT now()
        )
        """
    )

    columns = _table_columns(con, RAW_TABLE)

    if "data" not in columns:
        con.execute(f"ALTER TABLE {RAW_TABLE} ADD COLUMN data JSON")
        columns = _table_columns(con, RAW_TABLE)

    if "inserted_at" not in columns:
        con.execute(f"ALTER TABLE {RAW_TABLE} ADD COLUMN inserted_at TIMESTAMP DEFAULT now()")
        columns = _table_columns(con, RAW_TABLE)

    if "raw_json" in columns:
        _drop_legacy_raw_json_column(con, RAW_TABLE)
        columns = _table_columns(con, RAW_TABLE)

    if columns.get("data") != "JSON":
        raise ValueError(
            "La columna vinilos_raw.data no se pudo inicializar como JSON. "
            "Revisa la tabla manualmente antes de arrancar la app."
        )


def init_table():
    with closing(get_connection()) as con:
        _ensure_schema(con)


def exists(id_):
    with closing(get_connection()) as con:
        return (
            con.execute(
                f"SELECT 1 FROM {RAW_TABLE} WHERE id = ? LIMIT 1",
                (id_,),
            ).fetchone()
            is not None
        )


def get_info(id_):
    with closing(get_connection()) as con:
        row = con.execute(
            f"SELECT data FROM {RAW_TABLE} WHERE id = ?",
            (id_,),
        ).fetchone()

    if not row:
        return None

    data = _load_raw_json(row[0])
    artistas = _join_names(data.get("artists", []))
    titulo = str(data.get("title") or "").strip() or "(sin título)"
    año = data.get("year")

    texto = titulo if not artistas else f"{artistas} – {titulo}"
    if año:
        texto += f" ({año})"

    return texto


def get_data(id_):
    with closing(get_connection()) as con:
        row = con.execute(
            f"SELECT data FROM {RAW_TABLE} WHERE id = ?",
            (id_,),
        ).fetchone()

    if not row:
        return None

    return _load_raw_json(row[0])


def get_primary_image_url(id_):
    data = get_data(id_)
    if not isinstance(data, dict):
        return None

    images = data.get("images", []) or []
    for image in images:
        if not isinstance(image, dict):
            continue
        uri = str(image.get("uri") or "").strip()
        if uri:
            return uri
        uri150 = str(image.get("uri150") or "").strip()
        if uri150:
            return uri150

    for key in ("thumb", "cover_image"):
        value = str(data.get(key) or "").strip()
        if value:
            return value

    return None


def save(id_, payload, overwrite=False):
    with closing(get_connection()) as con:
        _ensure_schema(con)
        if overwrite:
            con.execute(f"DELETE FROM {RAW_TABLE} WHERE id = ?", (id_,))
        else:
            found = con.execute(
                f"SELECT 1 FROM {RAW_TABLE} WHERE id = ? LIMIT 1",
                (id_,),
            ).fetchone()
            if found:
                raise DuplicateViniloRawError(f"El ID {id_} ya existe en vinilos_raw")

        con.execute(
            f"INSERT INTO {RAW_TABLE} (id, data) VALUES (?, CAST(? AS JSON))",
            (id_, json.dumps(payload, ensure_ascii=False)),
        )

    return {"id": id_, "overwritten": bool(overwrite)}
