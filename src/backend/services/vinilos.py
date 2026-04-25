from contextlib import closing
import json
from datetime import datetime

from ..database import get_connection
from ..normalizers import normalizar_año


class ViniloNotFoundError(ValueError):
    pass


def _join_names(items):
    names = []
    for item in items or []:
        name = str((item or {}).get("name") or "").strip()
        if name:
            names.append(name)
    return ", ".join(names)


def _first_label_name(data):
    labels = data.get("labels", []) or []
    for label in labels:
        name = str((label or {}).get("name") or "").strip()
        if name:
            return name
    return None


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


def init_table():
    with closing(get_connection()) as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS vinilos (
                id TEXT PRIMARY KEY,
                tipo_articulo TEXT,
                nombre TEXT,
                artista TEXT,
                año INTEGER,
                sello TEXT,
                pais TEXT,
                duracion_total TEXT,
                estimated_weight REAL,
                generos TEXT,
                estilos TEXT,
                estado_conservacion TEXT,
                menor_precio REAL,
                precio REAL,
                estado_carga TEXT,
                estado_stock TEXT,
                tracklist TEXT,
                notas TEXT,
                updated_at TIMESTAMP
            )
            """
        )


def preparar():
    with closing(get_connection()) as con:
        raws = con.execute(
            """
            SELECT id, raw_json
            FROM vinilos_raw
            WHERE id NOT IN (SELECT id FROM vinilos)
            """
        ).fetchall()

        nuevos = 0
        for vid, raw_json in raws:
            data = json.loads(raw_json) if isinstance(raw_json, str) else raw_json

            con.execute(
                """
                INSERT INTO vinilos (
                    id, tipo_articulo, nombre, artista, año,
                    sello, pais, duracion_total, estimated_weight,
                    generos, estilos, menor_precio,
                    estado_carga, estado_stock,
                    tracklist, notas, updated_at
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
                    _first_label_name(data),
                    data.get("country"),
                    None,
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
            """
            SELECT id, nombre
            FROM vinilos
            ORDER BY id
            """
        ).fetchall()

    return [{"id": r[0], "nombre": r[1]} for r in rows]


def get_one(id_):
    with closing(get_connection()) as con:
        row = con.execute(
            """
            SELECT
                id, tipo_articulo, nombre, artista, año,
                sello, pais, duracion_total, estimated_weight,
                generos, estilos,
                estado_conservacion, menor_precio, precio,
                estado_carga, estado_stock, tracklist, notas
            FROM vinilos
            WHERE id = ?
            """,
            (id_,),
        ).fetchone()

    if not row:
        return None

    return {
        "id": row[0],
        "tipo_articulo": row[1],
        "nombre": row[2],
        "artista": row[3],
        "año": row[4],
        "sello": row[5],
        "pais": row[6],
        "duracion_total": row[7],
        "estimated_weight": row[8],
        "generos": row[9],
        "estilos": row[10],
        "estado_conservacion": row[11],
        "menor_precio": row[12],
        "precio": row[13],
        "estado_carga": row[14],
        "estado_stock": row[15],
        "tracklist": row[16],
        "notas": row[17],
    }


def list_all_full():
    with closing(get_connection()) as con:
        rows = con.execute(
            """
            SELECT *
            FROM vinilos
            ORDER BY nombre
            """
        ).fetchall()
        cols = [d[1] for d in con.execute("PRAGMA table_info(vinilos)").fetchall()]

    return [dict(zip(cols, row)) for row in rows]


def update(id_, data: dict):
    with closing(get_connection()) as con:
        exists = con.execute(
            "SELECT 1 FROM vinilos WHERE id = ? LIMIT 1",
            (id_,),
        ).fetchone()
        if not exists:
            raise ViniloNotFoundError(f"El vinilo {id_} no existe")

        con.execute(
            """
            UPDATE vinilos
            SET
                tipo_articulo = ?,
                nombre = ?,
                artista = ?,
                año = ?,
                sello = ?,
                pais = ?,
                duracion_total = ?,
                estimated_weight = ?,
                generos = ?,
                estilos = ?,
                tracklist = ?,
                estado_conservacion = ?,
                precio = ?,
                estado_carga = ?,
                estado_stock = ?,
                notas = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                data["tipo_articulo"],
                data["nombre"],
                data["artista"],
                normalizar_año(data["año"]),
                data["sello"],
                data["pais"],
                data["duracion_total"],
                data["estimated_weight"],
                data["generos"],
                data["estilos"],
                data["tracklist"],
                data["estado_conservacion"],
                data["precio"],
                data["estado_carga"],
                data["estado_stock"],
                data["notas"],
                datetime.now(),
                id_,
            ),
        )

    return get_one(id_)
