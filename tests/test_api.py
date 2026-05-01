import importlib
import sys
from pathlib import Path

import duckdb
from discogs_client.exceptions import HTTPError as DiscogsHTTPError
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

    with duckdb.connect(str(tmp_path / "vinilos.duckdb")) as con:
        tables = {str(row[0]) for row in con.execute("PRAGMA show_tables").fetchall()}
        assert "discogs_release_payloads" in tables
        assert "vinilos_raw" not in tables

        columns = {
            str(row[1]): str(row[2])
            for row in con.execute("PRAGMA table_info('discogs_release_payloads')").fetchall()
        }
        assert columns["data"] == "JSON"
        assert "raw_json" not in columns

        stored_title = con.execute(
            "SELECT json_extract_string(data, '$.title') FROM discogs_release_payloads WHERE id = ?",
            ("VIN-001",),
        ).fetchone()[0]
        assert stored_title == "Discovery"


def test_vinilos_raw_legacy_column_is_migrated_and_removed(tmp_path, monkeypatch):
    db_path = tmp_path / "vinilos.duckdb"
    with duckdb.connect(str(db_path)) as con:
        con.execute(
            """
            CREATE TABLE vinilos_raw (
                id TEXT PRIMARY KEY,
                raw_json TEXT,
                inserted_at TIMESTAMP DEFAULT now()
            )
            """
        )
        con.execute(
            "INSERT INTO vinilos_raw (id, raw_json) VALUES (?, ?)",
            (
                "VIN-LEGACY",
                '{"title":"Blue Train","artists":[{"name":"John Coltrane"}],"year":1957}',
            ),
        )

    app = _load_app(tmp_path, monkeypatch)
    client = TestClient(app)

    response = client.get("/vinilos_raw/info/VIN-LEGACY")
    assert response.status_code == 200
    assert "Blue Train" in response.json()["info"]

    with duckdb.connect(str(db_path)) as con:
        tables = {str(row[0]) for row in con.execute("PRAGMA show_tables").fetchall()}
        assert "discogs_release_payloads" in tables
        assert "vinilos_raw" not in tables

        columns = {
            str(row[1]): str(row[2])
            for row in con.execute("PRAGMA table_info('discogs_release_payloads')").fetchall()
        }
        assert columns["data"] == "JSON"
        assert "raw_json" not in columns

        stored_title = con.execute(
            "SELECT json_extract_string(data, '$.title') FROM discogs_release_payloads WHERE id = ?",
            ("VIN-LEGACY",),
        ).fetchone()[0]
        assert stored_title == "Blue Train"


def test_legacy_vinilos_schema_is_migrated_to_english_tables(tmp_path, monkeypatch):
    db_path = tmp_path / "vinilos.duckdb"
    with duckdb.connect(str(db_path)) as con:
        con.execute(
            """
            CREATE TABLE vinilos (
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
                detalle_estado_conservacion TEXT,
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
        con.execute(
            """
            INSERT INTO vinilos (
                id, tipo_articulo, nombre, artista, año, sello, pais,
                duracion_total, estimated_weight, generos, estilos,
                estado_conservacion, detalle_estado_conservacion, menor_precio,
                precio, estado_carga, estado_stock, tracklist, notas, updated_at
            )
            VALUES (
                'VIN-MIG',
                'LP',
                'A Love Supreme',
                'John Coltrane',
                1965,
                'Impulse!',
                'US',
                '32:48',
                180,
                'Jazz',
                'Modal',
                'VG+',
                'Carpeta con desgaste leve.',
                24.50,
                29.95,
                'Para actualizar',
                'En stock',
                'A1 - Acknowledgement (7:42)',
                'Notas heredadas',
                now()
            )
            """
        )
        con.execute(
            """
            CREATE TABLE vinilo_field_allowed_values (
                table_name TEXT,
                field_name TEXT,
                field_value TEXT,
                sort_order INTEGER DEFAULT 0,
                PRIMARY KEY (table_name, field_name, field_value)
            )
            """
        )
        con.execute(
            """
            INSERT INTO vinilo_field_allowed_values (table_name, field_name, field_value, sort_order)
            VALUES ('vinilos', 'tipo_articulo', 'LP', 0)
            """
        )

    app = _load_app(tmp_path, monkeypatch)
    client = TestClient(app)

    response = client.get("/vinilos/VIN-MIG")
    assert response.status_code == 200
    body = response.json()
    assert body["nombre"] == "A Love Supreme"
    assert body["sello"] == "Impulse!"
    assert body["estado_disco"] == "VG+"
    assert body["estado_funda"] is None
    assert body["comentarios_estado"] == "Carpeta con desgaste leve."

    options = client.get("/vinilos/options")
    assert options.status_code == 200
    assert "LP" in options.json()["allowed_values"]["tipo_articulo"]

    with duckdb.connect(str(db_path)) as con:
        tables = {str(row[0]) for row in con.execute("PRAGMA show_tables").fetchall()}
        assert "inventory_items" in tables
        assert "inventory_field_allowed_values" in tables
        assert "vinilos" not in tables
        assert "vinilo_field_allowed_values" not in tables

        columns = {
            str(row[1]): str(row[2])
            for row in con.execute("PRAGMA table_info('inventory_items')").fetchall()
        }
        assert "product_type" in columns
        assert "title" in columns
        assert "artists" in columns
        assert "labels" in columns
        assert "media_condition" in columns
        assert "sleeve_condition" in columns
        assert "condition_comments" in columns
        assert "listing_status" in columns
        assert "stock_status" in columns


def test_vinilos_options_expose_closed_values(tmp_path, monkeypatch):
    app = _load_app(tmp_path, monkeypatch)
    client = TestClient(app)

    response = client.get("/vinilos/options")

    assert response.status_code == 200
    allowed_values = response.json()["allowed_values"]
    assert "LP" in allowed_values["tipo_articulo"]
    assert allowed_values["estado_disco"][:4] == ["M", "NM or M-", "VG+", "VG"]
    assert allowed_values["estado_funda"][-3:] == ["Not Graded", "Generic", "No Cover"]


def test_discogs_search_returns_structured_rate_limit_message(tmp_path, monkeypatch):
    app = _load_app(tmp_path, monkeypatch)
    client = TestClient(app)

    main = importlib.import_module("src.backend.main")

    class FakeDiscogsClient:
        def search(self, *args, **kwargs):
            raise DiscogsHTTPError("You are making requests too quickly.", 429)

    monkeypatch.setattr(main, "get_client", lambda: FakeDiscogsClient())

    response = client.get("/discogs/search", params={"q": "miles davis"})

    assert response.status_code == 429
    detail = response.json()["detail"]
    assert detail["status_code"] == 429
    assert "límite" in detail["message"].lower() or "limitando" in detail["message"].lower()
    assert "upstream_message" in detail


def test_discogs_release_returns_structured_not_found_message(tmp_path, monkeypatch):
    app = _load_app(tmp_path, monkeypatch)
    client = TestClient(app)

    main = importlib.import_module("src.backend.main")

    class FakeRelease:
        data = {}

        def refresh(self):
            raise DiscogsHTTPError("Release not found.", 404)

    class FakeDiscogsClient:
        def release(self, release_id):
            return FakeRelease()

    monkeypatch.setattr(main, "get_client", lambda: FakeDiscogsClient())

    response = client.get("/discogs/release/999999999")

    assert response.status_code == 404
    detail = response.json()["detail"]
    assert detail["status_code"] == 404
    assert "no ha encontrado" in detail["message"].lower()
    assert "upstream_message" in detail


def test_prepare_calculates_total_duration_over_one_hour(tmp_path, monkeypatch):
    app = _load_app(tmp_path, monkeypatch)
    client = TestClient(app)

    save_response = client.post(
        "/vinilos_raw",
        json={
            "id": "VIN-003",
            "data": {
                "title": "Longform Sessions",
                "artists": [{"name": "Example Artist"}],
                "tracklist": [
                    {"position": "A1", "title": "Part I", "duration": "40:15"},
                    {"position": "B1", "title": "Part II", "duration": "24:45"},
                ],
            },
            "overwrite": False,
        },
    )
    assert save_response.status_code == 200

    prepare_response = client.post("/vinilos/preparar")
    assert prepare_response.status_code == 200

    prepared_response = client.get("/vinilos/VIN-003")
    assert prepared_response.status_code == 200
    assert prepared_response.json()["duracion_total"] == "1:05:00"


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

    prepared_response = client.get("/vinilos/VIN-002")
    assert prepared_response.status_code == 200
    prepared_vinilo = prepared_response.json()
    assert prepared_vinilo["tipo_articulo"] == "Vinilo"
    assert prepared_vinilo["duracion_total"] == "9:22"
    assert prepared_vinilo["estado_disco"] is None
    assert prepared_vinilo["estado_funda"] is None
    assert prepared_vinilo["comentarios_estado"] is None

    update_response = client.put(
        "/vinilos/VIN-002",
        json={
            "tipo_articulo": "LP",
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
            "estado_disco": "VG+",
            "estado_funda": "VG",
            "comentarios_estado": "Ligero desgaste superficial, reproducción sólida.",
            "precio": 29.99,
            "estado_carga": "Para subir",
            "estado_stock": "En stock",
            "notas": "Edición revisada",
        },
    )
    assert update_response.status_code == 200
    updated_vinilo = update_response.json()["vinilo"]
    assert updated_vinilo["nombre"] == "Kind of Blue"
    assert updated_vinilo["tipo_articulo"] == "LP"
    assert updated_vinilo["estado_disco"] == "VG+"
    assert updated_vinilo["estado_funda"] == "VG"
    assert updated_vinilo["comentarios_estado"] == "Ligero desgaste superficial, reproducción sólida."

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
    assert "comentarios_estado" in download_response.text
    assert "Kind of Blue" in download_response.text
    assert "VG+" in download_response.text
