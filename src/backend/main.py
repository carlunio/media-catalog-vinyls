import logging
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from src.project_meta import get_app_meta

from .config import EXPORTS_DIR
from .discogs_client import DiscogsClientConfigurationError, get_client
from .schemas.discogs import DiscogsSearchResult
from .schemas.vinilos import ViniloListItem, ViniloOut, ViniloUpdateRequest
from .schemas.vinilos_raw import ViniloRawIn
from .services import export, vinilos, vinilos_raw
from .services.vinilos import ViniloNotFoundError
from .services.vinilos_raw import DuplicateViniloRawError

logger = logging.getLogger(__name__)
APP_META = get_app_meta()

app = FastAPI(title=f"{APP_META.app_name} API", version=APP_META.version)

vinilos_raw.init_table()
vinilos.init_table()


def _raise_discogs_error(exc: Exception) -> None:
    if isinstance(exc, DiscogsClientConfigurationError):
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    message = str(exc).strip() or exc.__class__.__name__
    lowered = message.lower()
    if "429" in lowered or "rate limit" in lowered or "too many requests" in lowered:
        raise HTTPException(status_code=429, detail=message) from exc

    raise HTTPException(status_code=502, detail=message) from exc


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/discogs/search", response_model=List[DiscogsSearchResult])
def search_discogs(q: str):
    try:
        client = get_client()
        results = list(client.search(q, type="release"))[:5]
        return [
            {"id": r.id, "title": r.title, "thumb": getattr(r, "thumb", None)}
            for r in results
        ]
    except Exception as exc:
        _raise_discogs_error(exc)


@app.get("/discogs/release/{release_id}")
def get_release(release_id: int):
    try:
        client = get_client()
        release = client.release(release_id)
        release.refresh()
        return release.data
    except Exception as exc:
        logger.exception("Discogs release lookup failed", extra={"release_id": release_id})
        _raise_discogs_error(exc)


@app.post("/vinilos_raw")
def save_raw(payload: ViniloRawIn):
    try:
        result = vinilos_raw.save(payload.id, payload.data, payload.overwrite)
    except DuplicateViniloRawError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True, **result}


@app.get("/vinilos_raw/exists/{id_}")
def vinilo_raw_exists(id_: str):
    return {"exists": vinilos_raw.exists(id_)}


@app.get("/vinilos_raw/info/{id_}")
def vinilo_raw_info(id_: str):
    info = vinilos_raw.get_info(id_)
    if not info:
        raise HTTPException(status_code=404, detail="No existe")
    return {"info": info}


@app.post("/vinilos/preparar")
def preparar_vinilos():
    creados = vinilos.preparar()
    return {"creados": creados}


@app.get("/vinilos", response_model=List[ViniloListItem])
def list_vinilos():
    return vinilos.list_all()


@app.get("/vinilos/{id_}", response_model=ViniloOut)
def get_vinilo(id_: str):
    data = vinilos.get_one(id_)
    if not data:
        raise HTTPException(status_code=404, detail="Vinilo no encontrado")
    return data


@app.put("/vinilos/{id_}")
def update_vinilo(id_: str, payload: ViniloUpdateRequest):
    try:
        serialized = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
        updated = vinilos.update(id_, serialized)
    except ViniloNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "vinilo": updated}


@app.get("/export/vinilos/txt")
def export_vinilos_txt():
    result = export.export_vinilos_txt()
    path = Path(str(result["path"]))
    return {
        "ok": True,
        "path": str(path),
        "filename": str(result["filename"]),
        "rows": int(result["rows"]),
    }


@app.get("/export/vinilos/file")
def export_vinilos_file(filename: str):
    name = str(filename or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="filename is required")
    if "/" in name or "\\" in name:
        raise HTTPException(status_code=400, detail="invalid filename")
    if not name.lower().endswith(".txt"):
        raise HTTPException(status_code=400, detail="only .txt exports are allowed")

    path = EXPORTS_DIR / name
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="export file not found")

    return FileResponse(
        path=str(path),
        media_type="text/plain",
        filename=name,
    )
