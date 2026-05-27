import logging
from pathlib import Path
from typing import Any, List

import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from discogs_client.exceptions import AuthorizationError, HTTPError as DiscogsHTTPError

from src.project_meta import get_app_meta

from .config import EXPORTS_DIR
from .discogs_client import DiscogsClientConfigurationError, get_client
from .schemas.discogs import DiscogsSearchResult
from .schemas.vinilos import ExportUploadRequest, ViniloListItem, ViniloOut, ViniloUpdateRequest
from .schemas.vinilos_raw import ViniloRawIn
from .services import export, vinilos, vinilos_raw
from .services.vinilos import ViniloNotFoundError
from .services.vinilos_raw import DuplicateViniloRawError

logger = logging.getLogger(__name__)
APP_META = get_app_meta()

app = FastAPI(title=f"{APP_META.app_name} API", version=APP_META.version)

vinilos_raw.init_table()
vinilos.init_table()


def _discogs_error_detail(status_code: int, upstream_message: str | None = None) -> dict[str, Any]:
    base: dict[int, dict[str, str]] = {
        400: {
            "title": "Solicitud no válida a Discogs",
            "message": "Discogs no ha aceptado la búsqueda o alguno de sus parámetros.",
            "hint": "Prueba con una búsqueda más simple o revisa que el valor enviado tenga sentido.",
        },
        401: {
            "title": "Autenticación rechazada por Discogs",
            "message": "Discogs no ha aceptado las credenciales de la aplicación.",
            "hint": "Revisa `DISCOGS_TOKEN` y confirma que siga siendo válido.",
        },
        403: {
            "title": "Acceso denegado por Discogs",
            "message": "Discogs ha rechazado la petición aunque la autenticación exista.",
            "hint": "Puede deberse a restricciones del recurso, permisos insuficientes o bloqueo temporal.",
        },
        404: {
            "title": "Recurso no encontrado en Discogs",
            "message": "Discogs no ha encontrado el release o recurso solicitado.",
            "hint": "Prueba con otro resultado de búsqueda o vuelve a lanzar la consulta.",
        },
        405: {
            "title": "Método no permitido en Discogs",
            "message": "Discogs ha rechazado el tipo de petición enviado.",
            "hint": "Es un problema técnico del cliente; conviene revisar la integración.",
        },
        422: {
            "title": "Discogs no pudo procesar la petición",
            "message": "Discogs ha recibido la solicitud pero no puede interpretarla correctamente.",
            "hint": "Suele deberse a parámetros inconsistentes o formatos no aceptados por la API.",
        },
        429: {
            "title": "Límite de peticiones alcanzado en Discogs",
            "message": "Discogs está limitando temporalmente las consultas de la aplicación.",
            "hint": "Espera unos segundos y vuelve a intentarlo para evitar el rate limit.",
        },
        500: {
            "title": "Error interno en Discogs",
            "message": "Discogs ha devuelto un error interno al procesar la petición.",
            "hint": "Lo mejor es reintentar más tarde; el problema parece estar del lado de Discogs.",
        },
        502: {
            "title": "Respuesta inválida desde Discogs",
            "message": "Discogs ha respondido de forma inesperada o incompleta.",
            "hint": "Reintenta la consulta y, si persiste, conviene revisar el estado del servicio.",
        },
        503: {
            "title": "Discogs no está disponible",
            "message": "Discogs no puede atender la petición en este momento.",
            "hint": "Puede ser una caída temporal o mantenimiento; conviene intentarlo más tarde.",
        },
        504: {
            "title": "Tiempo de espera agotado en Discogs",
            "message": "Discogs ha tardado demasiado en responder.",
            "hint": "Vuelve a intentarlo en unos segundos o con una consulta más acotada.",
        },
    }
    detail = dict(
        base.get(
            status_code,
            {
                "title": "Error desconocido en Discogs",
                "message": "Discogs ha devuelto una respuesta no prevista por la aplicación.",
                "hint": "Conviene reintentar la operación y revisar el detalle técnico si persiste.",
            },
        )
    )
    detail["status_code"] = int(status_code)
    if upstream_message:
        detail["upstream_message"] = upstream_message
    return detail


def _raise_discogs_error(exc: Exception) -> None:
    if isinstance(exc, DiscogsClientConfigurationError):
        raise HTTPException(
            status_code=503,
            detail={
                "title": "Discogs no está configurado",
                "message": "La aplicación no puede usar Discogs porque falta su configuración.",
                "hint": "Revisa `DISCOGS_TOKEN` antes de volver a intentarlo.",
                "status_code": 503,
                "upstream_message": str(exc),
            },
        ) from exc

    if isinstance(exc, (DiscogsHTTPError, AuthorizationError)):
        status_code = int(getattr(exc, "status_code", 502) or 502)
        raise HTTPException(
            status_code=status_code,
            detail=_discogs_error_detail(status_code, str(exc).strip() or None),
        ) from exc

    if isinstance(exc, requests.Timeout):
        raise HTTPException(
            status_code=504,
            detail=_discogs_error_detail(504, str(exc).strip() or None),
        ) from exc

    if isinstance(exc, requests.RequestException):
        raise HTTPException(
            status_code=503,
            detail=_discogs_error_detail(503, str(exc).strip() or None),
        ) from exc

    message = str(exc).strip() or exc.__class__.__name__
    raise HTTPException(status_code=502, detail=_discogs_error_detail(502, message)) from exc


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


@app.get("/vinilos/options")
def vinilos_options():
    return {
        "allowed_values": vinilos.get_vinilos_allowed_values(),
        "tc_sections": vinilos.get_tc_sections_catalog(),
    }


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


@app.get("/export/vinilos/preview")
def export_vinilos_preview():
    preview = export.get_export_preview()
    return {
        "ok": True,
        "columns": preview["columns"],
        "rows": preview["rows"],
        "ids": preview["ids"],
        "rows_count": int(preview["rows_count"]),
    }


@app.get("/export/vinilos/txt")
def export_vinilos_txt():
    return export_vinilos_csv()


@app.get("/export/vinilos/csv")
def export_vinilos_csv():
    result = export.export_vinilos_csv()
    path = Path(str(result["path"]))
    return {
        "ok": True,
        "path": str(path),
        "filename": str(result["filename"]),
        "rows": int(result["rows"]),
        "ids": result["ids"],
    }


@app.post("/export/vinilos/txt")
def export_vinilos_txt_selected(payload: ExportUploadRequest):
    return export_vinilos_csv_selected(payload)


@app.post("/export/vinilos/csv")
def export_vinilos_csv_selected(payload: ExportUploadRequest):
    result = export.export_vinilos_csv(ids=payload.ids)
    path = Path(str(result["path"]))
    return {
        "ok": True,
        "path": str(path),
        "filename": str(result["filename"]),
        "rows": int(result["rows"]),
        "ids": result["ids"],
    }


@app.get("/export/vinilos/file")
def export_vinilos_file(filename: str):
    name = str(filename or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="filename is required")
    if "/" in name or "\\" in name:
        raise HTTPException(status_code=400, detail="invalid filename")
    if not name.lower().endswith((".csv", ".txt")):
        raise HTTPException(status_code=400, detail="only .csv or .txt exports are allowed")

    path = EXPORTS_DIR / name
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="export file not found")

    return FileResponse(
        path=str(path),
        media_type="text/csv" if name.lower().endswith(".csv") else "text/plain",
        filename=name,
    )


@app.post("/export/vinilos/clear-operation")
def export_vinilos_clear_operation(payload: ExportUploadRequest):
    result = export.clear_exported_items_listing_status(payload.ids)
    return {
        "ok": True,
        "updated": int(result["updated"]),
        "ids": result["ids"],
    }


@app.post("/export/vinilos/mark-uploaded")
def export_vinilos_mark_uploaded(payload: ExportUploadRequest):
    return export_vinilos_clear_operation(payload)
