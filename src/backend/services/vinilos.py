import json
from datetime import datetime
from ..database import get_connection
from ..normalizers import normalizar_año


# =========================
# INIT
# =========================
def init_table():
    con = get_connection()
    con.execute("""
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
    """)
    con.close()


# =========================
# FASE A: PREPARAR
# =========================
def preparar():
    con = get_connection()

    raws = con.execute("""
        SELECT id, raw_json
        FROM vinilos_raw
        WHERE id NOT IN (SELECT id FROM vinilos)
    """).fetchall()

    nuevos = 0

    for vid, raw_json in raws:
        data = json.loads(raw_json)

        artista = ", ".join(a.get("name") for a in data.get("artists", []))
        año = normalizar_año(data.get("year"))

        tracklist = []
        for t in data.get("tracklist", []):
            pos = t.get("position", "")
            title = t.get("title", "")
            dur = t.get("duration", "")
            if dur:
                tracklist.append(f"{pos} - {title} ({dur})")
            else:
                tracklist.append(f"{pos} - {title}")

        con.execute("""
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
        """, (
            vid,
            data.get("title"),
            artista,
            año,
            data.get("labels", [{}])[0].get("name"),
            data.get("country"),
            None,
            data.get("estimated_weight"),
            ", ".join(data.get("genres", [])),
            ", ".join(data.get("styles", [])),
            data.get("lowest_price"),
            "\n".join(tracklist),
            data.get("notes"),
            datetime.now()
        ))

        nuevos += 1

    con.close()
    return nuevos


# =========================
# LISTAR
# =========================
def list_all():
    con = get_connection()
    rows = con.execute("""
        SELECT id, nombre
        FROM vinilos
        ORDER BY id
    """).fetchall()
    con.close()

    return [{"id": r[0], "nombre": r[1]} for r in rows]


# =========================
# OBTENER UNO
# =========================
def get_one(id_):
    con = get_connection()
    row = con.execute("""
        SELECT
            id, tipo_articulo, nombre, artista, año,
            sello, pais, duracion_total, estimated_weight,
            generos, estilos,
            estado_conservacion, menor_precio, precio,
            estado_carga, estado_stock, tracklist, notas
        FROM vinilos
        WHERE id = ?
    """, (id_,)).fetchone()
    con.close()

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


# =========================
# ACTUALIZAR
# =========================
def update(id_, data: dict):
    con = get_connection()

    con.execute("""
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
    """, (
        data.get("tipo_articulo"),
        data.get("nombre"),
        data.get("artista"),
        normalizar_año(data.get("año")),
        data.get("sello"),
        data.get("pais"),
        data.get("duracion_total"),
        data.get("estimated_weight"),
        data.get("generos"),
        data.get("estilos"),
        data.get("tracklist"),
        data.get("estado_conservacion"),
        data.get("precio"),
        data.get("estado_carga"),
        data.get("estado_stock"),
        data.get("notas"),
        datetime.now(),
        id_
    ))

    con.close()
