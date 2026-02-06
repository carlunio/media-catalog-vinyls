from fastapi import FastAPI, HTTPException

from .discogs_client import get_client
from .services import export, vinilos, vinilos_raw

app = FastAPI()

# Inicialización de tablas
vinilos_raw.init_table()
vinilos.init_table()

client = get_client()

# =========================
# DISCOGS
# =========================

from typing import List

from .schemas.discogs import DiscogsSearchResult


@app.get("/discogs/search", response_model=List[DiscogsSearchResult])
def search_discogs(q: str):
    try:
        results = list(client.search(q, type="release"))[:5]
        return [
            {"id": r.id, "title": r.title, "thumb": getattr(r, "thumb", None)}
            for r in results
        ]
    except Exception as e:
        raise HTTPException(status_code=429, detail=str(e))


@app.get("/discogs/release/{release_id}")
def get_release(release_id: int):
    try:
        release = client.release(release_id)

        release.refresh()

        return release.data  

    except Exception as e:
        print("ERROR DISCOSG RELEASE:", repr(e))
        raise HTTPException(status_code=500, detail=str(e))


# =========================
# VINILOS_RAW
# =========================
from .schemas.vinilos_raw import ViniloRawIn


@app.post("/vinilos_raw")
def save_raw(payload: ViniloRawIn):
    vinilos_raw.save(payload.id, payload.data, payload.overwrite)
    return {"ok": True}


# 🔹 AÑADIDO: existe
@app.get("/vinilos_raw/exists/{id_}")
def vinilo_raw_exists(id_: str):
    return {"exists": vinilos_raw.exists(id_)}


# 🔹 AÑADIDO: info
@app.get("/vinilos_raw/info/{id_}")
def vinilo_raw_info(id_: str):
    info = vinilos_raw.get_info(id_)
    if not info:
        raise HTTPException(status_code=404, detail="No existe")
    return {"info": info}


# =========================
# VINILOS (PROCESADOS)
# =========================
@app.post("/vinilos/preparar")
def preparar_vinilos():
    creados = vinilos.preparar()
    return {"creados": creados}


@app.get("/vinilos")
def list_vinilos():
    return vinilos.list_all()


@app.get("/vinilos/{id_}")
def get_vinilo(id_: str):
    data = vinilos.get_one(id_)
    if not data:
        raise HTTPException(status_code=404, detail="Vinilo no encontrado")
    return data


@app.put("/vinilos/{id_}")
def update_vinilo(id_: str, payload: dict):
    vinilos.update(id_, payload)
    return {"ok": True}


# =========================
# EXPORTACIÓN
# =========================

from pathlib import Path


@app.get("/export/vinilos/txt")
def export_vinilos_txt():
    output = Path("exports/vinilos.txt")
    export.export_vinilos_txt(output)
    return {"ok": True, "path": str(output)}
