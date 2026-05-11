from contextlib import closing
import json

from ..config import DB_SCHEMA
from ..database import get_connection


class DuplicateViniloRawError(ValueError):
    pass


RAW_TABLE = "discogs_release_payloads"
MAIN_SCHEMA = "main"


def _qualified_table(schema_name: str, table_name: str) -> str:
    return f"{schema_name}.{table_name}"


RAW_TABLE_REF = _qualified_table(DB_SCHEMA, RAW_TABLE)


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


def _table_columns(con, schema_name, table_name):
    rows = con.execute(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = ? AND table_name = ?
        """,
        (schema_name, table_name),
    ).fetchall()
    return {
        str(row[0] or "").strip(): str(row[1] or "").strip().upper()
        for row in rows
        if str(row[0] or "").strip()
    }


def _ensure_schema(con):
    if DB_SCHEMA != MAIN_SCHEMA:
        con.execute(f"CREATE SCHEMA IF NOT EXISTS {DB_SCHEMA}")
    con.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {RAW_TABLE_REF} (
            id TEXT PRIMARY KEY,
            data JSON,
            inserted_at TIMESTAMP DEFAULT now()
        )
        """
    )
    con.execute(f"ALTER TABLE {RAW_TABLE_REF} ADD COLUMN IF NOT EXISTS data JSON")
    con.execute(f"ALTER TABLE {RAW_TABLE_REF} ADD COLUMN IF NOT EXISTS inserted_at TIMESTAMP DEFAULT now()")

    columns = _table_columns(con, DB_SCHEMA, RAW_TABLE)
    if columns.get("data") != "JSON":
        raise ValueError(
            f"La columna {RAW_TABLE_REF}.data debe ser de tipo JSON en el esquema activo."
        )


def init_table():
    with closing(get_connection()) as con:
        _ensure_schema(con)


def exists(id_):
    with closing(get_connection()) as con:
        return (
            con.execute(
                f"SELECT 1 FROM {RAW_TABLE_REF} WHERE id = ? LIMIT 1",
                (id_,),
            ).fetchone()
            is not None
        )


def get_info(id_):
    with closing(get_connection()) as con:
        row = con.execute(
            f"SELECT data FROM {RAW_TABLE_REF} WHERE id = ?",
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
            f"SELECT data FROM {RAW_TABLE_REF} WHERE id = ?",
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
            con.execute(f"DELETE FROM {RAW_TABLE_REF} WHERE id = ?", (id_,))
        else:
            found = con.execute(
                f"SELECT 1 FROM {RAW_TABLE_REF} WHERE id = ? LIMIT 1",
                (id_,),
            ).fetchone()
            if found:
                raise DuplicateViniloRawError(f"El ID {id_} ya existe en {RAW_TABLE}")

        con.execute(
            f"INSERT INTO {RAW_TABLE_REF} (id, data) VALUES (?, CAST(? AS JSON))",
            (id_, json.dumps(payload, ensure_ascii=False)),
        )

    return {"id": id_, "overwritten": bool(overwrite)}
