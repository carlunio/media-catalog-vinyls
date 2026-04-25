import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient


def _load_app(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "vinilos.duckdb"))
    monkeypatch.setenv("EXPORTS_DIR", str(tmp_path / "exports"))
    monkeypatch.delenv("DISCOGS_TOKEN", raising=False)

    for module_name in list(sys.modules):
        if module_name == "src" or module_name.startswith("src."):
            sys.modules.pop(module_name, None)
        if module_name == "backend" or module_name.startswith("backend."):
            sys.modules.pop(module_name, None)

    main = importlib.import_module("src.backend.main")
    return main.app


def test_backend_imports_without_discogs_token(tmp_path, monkeypatch):
    app = _load_app(tmp_path, monkeypatch)
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_vinilos_raw_duplicate_returns_conflict(tmp_path, monkeypatch):
    app = _load_app(tmp_path, monkeypatch)
    client = TestClient(app)

    payload = {
        "id": "VIN-001",
        "data": {
            "title": "Discovery",
            "artists": [{"name": "Daft Punk"}],
            "year": 2001,
        },
        "overwrite": False,
    }

    first = client.post("/vinilos_raw", json=payload)
    second = client.post("/vinilos_raw", json=payload)

    assert first.status_code == 200
    assert second.status_code == 409


def test_prepare_update_and_export_flow(tmp_path, monkeypatch):
    app = _load_app(tmp_path, monkeypatch)
    client = TestClient(app)

    save_response = client.post(
        "/vinilos_raw",
        json={
            "id": "VIN-002",
            "data": {
                "title": "Kind of Blue",
                "artists": [{"name": "Miles Davis"}],
                "year": "1959",
                "labels": [{"name": "Columbia"}],
                "genres": ["Jazz"],
                "styles": ["Modal"],
                "tracklist": [{"position": "A1", "title": "So What", "duration": "9:22"}],
                "notes": "Classic.",
            },
            "overwrite": False,
        },
    )
    assert save_response.status_code == 200

    prepare_response = client.post("/vinilos/preparar")
    assert prepare_response.status_code == 200
    assert prepare_response.json()["creados"] == 1

    update_response = client.put(
        "/vinilos/VIN-002",
        json={
            "tipo_articulo": "Vinilo",
            "nombre": "Kind of Blue",
            "artista": "Miles Davis",
            "año": 1959,
            "sello": "Columbia",
            "pais": "US",
            "duracion_total": "45:44",
            "estimated_weight": 180,
            "generos": "Jazz",
            "estilos": "Modal",
            "tracklist": "A1 - So What (9:22)",
            "estado_conservacion": "Muy bueno",
            "precio": 29.99,
            "estado_carga": "Para subir",
            "estado_stock": "En stock",
            "notas": "Edición revisada",
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["vinilo"]["nombre"] == "Kind of Blue"

    export_response = client.get("/export/vinilos/txt")
    assert export_response.status_code == 200
    export_payload = export_response.json()
    assert export_payload["filename"].endswith(".txt")
    assert export_payload["rows"] == 1

    download_response = client.get(
        "/export/vinilos/file",
        params={"filename": export_payload["filename"]},
    )
    assert download_response.status_code == 200
    assert "Kind of Blue" in download_response.text
