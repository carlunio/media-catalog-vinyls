import json
from ..database import get_connection


def init_table():
    con = get_connection()
    con.execute("""
        CREATE TABLE IF NOT EXISTS vinilos_raw (
            id TEXT PRIMARY KEY,
            raw_json JSON,
            inserted_at TIMESTAMP DEFAULT now()
        )
    """)
    con.close()


def exists(id_):
    con = get_connection()
    exists = con.execute(
        "SELECT 1 FROM vinilos_raw WHERE id = ? LIMIT 1",
        (id_,)
    ).fetchone() is not None
    con.close()
    return exists


def get_info(id_):
    con = get_connection()
    row = con.execute(
        "SELECT raw_json FROM vinilos_raw WHERE id = ?",
        (id_,)
    ).fetchone()
    con.close()

    if not row:
        return None

    data = json.loads(row[0])
    artistas = ", ".join(a.get("name") for a in data.get("artists", []))
    titulo = data.get("title")
    año = data.get("year")

    texto = f"{artistas} – {titulo}"
    if año:
        texto += f" ({año})"

    return texto


def save(id_, raw_json, overwrite=False):
    con = get_connection()

    if overwrite:
        con.execute("DELETE FROM vinilos_raw WHERE id = ?", (id_,))
    else:
        # seguridad extra por si acaso
        exists = con.execute(
            "SELECT 1 FROM vinilos_raw WHERE id = ? LIMIT 1",
            (id_,)
        ).fetchone()
        if exists:
            con.close()
            raise ValueError("ID already exists")

    con.execute(
        "INSERT INTO vinilos_raw (id, raw_json) VALUES (?, ?)",
        (id_, json.dumps(raw_json))
    )

    con.close()
