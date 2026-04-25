from contextlib import closing
import json

from ..database import get_connection


class DuplicateViniloRawError(ValueError):
    pass


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


def init_table():
    with closing(get_connection()) as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS vinilos_raw (
                id TEXT PRIMARY KEY,
                raw_json JSON,
                inserted_at TIMESTAMP DEFAULT now()
            )
            """
        )


def exists(id_):
    with closing(get_connection()) as con:
        return (
            con.execute(
                "SELECT 1 FROM vinilos_raw WHERE id = ? LIMIT 1",
                (id_,),
            ).fetchone()
            is not None
        )


def get_info(id_):
    with closing(get_connection()) as con:
        row = con.execute(
            "SELECT raw_json FROM vinilos_raw WHERE id = ?",
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


def save(id_, raw_json, overwrite=False):
    with closing(get_connection()) as con:
        if overwrite:
            con.execute("DELETE FROM vinilos_raw WHERE id = ?", (id_,))
        else:
            found = con.execute(
                "SELECT 1 FROM vinilos_raw WHERE id = ? LIMIT 1",
                (id_,),
            ).fetchone()
            if found:
                raise DuplicateViniloRawError(f"El ID {id_} ya existe en vinilos_raw")

        con.execute(
            "INSERT INTO vinilos_raw (id, raw_json) VALUES (?, ?)",
            (id_, json.dumps(raw_json, ensure_ascii=False)),
        )

    return {"id": id_, "overwritten": bool(overwrite)}
