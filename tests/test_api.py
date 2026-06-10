import importlib
import sys
from pathlib import Path

import duckdb
from discogs_client.exceptions import HTTPError as DiscogsHTTPError
from fastapi.testclient import TestClient

TESTS_DIR = Path(__file__).resolve().parent
TC_SECTIONS_FIXTURE_PATH = TESTS_DIR / "fixtures" / "secciones.csv"


def _importamatic_template_columns() -> list[str]:
    return importlib.import_module("src.backend.services.vinilos").IMPORTAMATIC_EXPORT_COLUMNS


def _load_app(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "vinyls.duckdb"))
    monkeypatch.setenv("EXPORTS_DIR", str(tmp_path / "exports"))
    monkeypatch.setenv("TC_SECTIONS_CSV_PATH", str(TC_SECTIONS_FIXTURE_PATH))
    monkeypatch.setenv("IMPORTAMATIC_OTHERS_FIXED_COST", "4.5")
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

    with duckdb.connect(str(tmp_path / "vinyls.duckdb")) as con:
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


def test_vinilos_raw_schema_is_initialized(tmp_path, monkeypatch):
    _load_app(tmp_path, monkeypatch)
    db_path = tmp_path / "vinyls.duckdb"
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


def test_items_schema_and_export_view_are_initialized(tmp_path, monkeypatch):
    db_path = tmp_path / "vinyls.duckdb"
    app = _load_app(tmp_path, monkeypatch)
    client = TestClient(app)

    options = client.get("/vinilos/options")
    assert options.status_code == 200
    assert "tipo_articulo" not in options.json()["allowed_values"]
    tc_sections = options.json()["tc_sections"]
    assert tc_sections["root_key"]
    tc_leaf_nodes = {
        str(node["section_id"]): node
        for node in tc_sections["nodes"]
        if isinstance(node, dict) and node.get("section_id")
    }
    assert tc_leaf_nodes["450"]["display_path"] == "CD > Clásica, Ópera, Zarzuela y Marchas"
    assert tc_leaf_nodes["376"]["display_path"] == (
        "Discos > LP Vinilo > Pop - Rock > Internacional de los 50 y 60"
    )
    assert tc_leaf_nodes["924"]["display_path"] == "Discos > LP Vinilo > Pop - Rock > Internacional de los 70"
    assert tc_leaf_nodes["466"]["display_path"] == "Discos > LP Vinilo > Reggae - Ska"
    assert tc_leaf_nodes["467"]["display_path"] == "Discos > LP Vinilo > Punk - Hard Core"

    with duckdb.connect(str(db_path)) as con:
        tables = {str(row[0]) for row in con.execute("PRAGMA show_tables").fetchall()}
        assert "items" in tables
        assert "export" in tables
        assert "inventory_field_allowed_values" in tables
        assert "tc_sections" in tables
        assert "vinilos" not in tables
        assert "inventory_items" not in tables
        assert "vinilo_field_allowed_values" not in tables

        columns = {
            str(row[1]): str(row[2])
            for row in con.execute("PRAGMA table_info('items')").fetchall()
        }
        assert "product_type" in columns
        assert "title" in columns
        assert "artists" in columns
        assert "labels" in columns
        assert "media_condition" in columns
        assert "sleeve_condition" in columns
        assert "condition_comments" in columns
        assert "tc_condition" in columns
        assert "listing_status" in columns
        assert "stock_status" in columns
        assert columns["tc_section"] == "VARCHAR"

        tc_section_columns = {
            str(row[1]): str(row[2])
            for row in con.execute("PRAGMA table_info('tc_sections')").fetchall()
        }
        assert tc_section_columns["section_id"] == "VARCHAR"
        assert tc_section_columns["path_labels"] == "VARCHAR[]"
        assert tc_section_columns["path_keys"] == "VARCHAR[]"

        con.execute(
            """
            INSERT INTO items (
                id, product_type, title, artists, year,
                labels, country, total_duration, estimated_weight,
                genres, styles, media_condition, sleeve_condition, condition_comments,
                tc_condition, tc_section,
                lowest_price, sale_price, listing_status, stock_status,
                tracklist, notes, updated_at
            )
            VALUES (
                'VIN-INIT', 'Vinilo, LP', 'A Love Supreme', 'John Coltrane', 1965,
                'Impulse!', 'US', '32:48', 180,
                'Jazz', 'Modal', 'VG+', 'VG', 'Carpeta con desgaste leve.',
                '4', '376',
                24.50, 29.95, 'CAMBIO', 'En stock',
                'A1 - Acknowledgement (7:42)', 'Notas iniciales', now()
            )
            """
        )

        export_cur = con.execute('SELECT * FROM "export"')
        export_columns = [desc[0] for desc in export_cur.description]
        export_rows = export_cur.fetchall()
        assert export_columns == _importamatic_template_columns()
        assert len(export_rows) == 1
        assert export_rows[0][0] == "VIN-INIT"
        assert export_rows[0][1] == "A Love Supreme"
        assert "<p><strong>Formato:</strong> Vinilo, LP</p>" in export_rows[0][2]
        assert "<p><strong>Año:</strong> 1965</p>" in export_rows[0][2]
        assert "<p><strong>Estado del vinilo:</strong>" not in export_rows[0][2]
        assert "<p><strong>Estado de la funda:</strong>" not in export_rows[0][2]
        assert (
            "<p><strong>Comentarios de conservación:</strong> Carpeta con desgaste leve.</p>"
            in export_rows[0][2]
        )
        assert (
            "<p><strong>Tracklist:</strong></p><ul><li>A1 - Acknowledgement (7:42)</li></ul>"
            in export_rows[0][2]
        )
        assert export_rows[0][4] == "29,95"
        assert export_rows[0][5] == "CAMBIO"
        assert export_rows[0][6] == "376"
        assert export_rows[0][7] == "4"
        assert export_rows[0][11] == "Otros"
        assert export_rows[0][12] == "4,5"

        con.execute(
            """
            INSERT INTO items (
                id, title, media_condition, sleeve_condition, listing_status, updated_at
            )
            VALUES ('VIN-LEGACY', 'Legacy condition', 'NM or M-', 'P', 'ALTA', now())
            """
        )

    importlib.import_module("src.backend.services.vinilos").init_table()

    with duckdb.connect(str(db_path)) as con:
        legacy_conditions = con.execute(
            "SELECT media_condition, sleeve_condition FROM items WHERE id = 'VIN-LEGACY'"
        ).fetchone()
        assert legacy_conditions == ("NM", "F")

    response = client.get("/vinilos/VIN-INIT")
    assert response.status_code == 200
    body = response.json()
    assert body["nombre"] == "A Love Supreme"
    assert body["tipo_articulo"] == "Vinilo, LP"
    assert body["sello"] == "Impulse!"
    assert body["estado_disco"] == "VG+"
    assert body["estado_funda"] == "VG"
    assert body["comentarios_estado"] == "Carpeta con desgaste leve."
    assert body["estado_tc"] == "4"


def test_vinilos_options_expose_closed_values(tmp_path, monkeypatch):
    app = _load_app(tmp_path, monkeypatch)
    client = TestClient(app)

    response = client.get("/vinilos/options")

    assert response.status_code == 200
    allowed_values = response.json()["allowed_values"]
    assert "tipo_articulo" not in allowed_values
    assert allowed_values["estado_disco"][:4] == ["M", "NM", "VG+", "VG"]
    assert "P" not in allowed_values["estado_disco"]
    assert allowed_values["estado_funda"][-3:] == ["Not Graded", "Generic", "No Cover"]
    assert "P" not in allowed_values["estado_funda"]
    assert allowed_values["estado_tc"] == ["5", "4", "3", "2", "1"]
    assert allowed_values["estado_carga"] == ["ALTA", "CAMBIO", "BAJA"]


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


def test_prepare_builds_credits_from_extraartists(tmp_path, monkeypatch):
    app = _load_app(tmp_path, monkeypatch)
    client = TestClient(app)

    save_response = client.post(
        "/vinilos_raw",
        json={
            "id": "VIN-003B",
            "data": {
                "title": "Nevermind",
                "artists": [{"name": "Nirvana"}],
                "extraartists": [
                    {"name": "Chris Novoselic", "role": "Bass"},
                    {"name": "Dave Grohl", "role": "Drums"},
                    {"name": "Kurt Cobain", "role": "Guitar, Vocals"},
                    {"name": "Nirvana", "role": "Written-By"},
                ],
            },
            "overwrite": False,
        },
    )
    assert save_response.status_code == 200

    prepare_response = client.post("/vinilos/preparar")
    assert prepare_response.status_code == 200

    prepared_response = client.get("/vinilos/VIN-003B")
    assert prepared_response.status_code == 200
    assert prepared_response.json()["creditos"] == (
        "Bass – Chris Novoselic\n"
        "Drums – Dave Grohl\n"
        "Guitar, Vocals – Kurt Cobain\n"
        "Written-By – Nirvana"
    )


def test_prepare_builds_multiple_discogs_formats(tmp_path, monkeypatch):
    app = _load_app(tmp_path, monkeypatch)
    client = TestClient(app)

    save_response = client.post(
        "/vinilos_raw",
        json={
            "id": "VIN-004",
            "data": {
                "title": "Clockwork Bootleg",
                "artists": [{"name": "Example Artist"}],
                "formats": [
                    {
                        "name": "Vinyl",
                        "qty": "1",
                        "descriptions": ["LP", "Unofficial Release", "Picture Disc"],
                        "text": "Clock",
                    },
                    {
                        "name": "Box Set",
                        "qty": "1",
                        "descriptions": [],
                    },
                ],
            },
            "overwrite": False,
        },
    )
    assert save_response.status_code == 200

    prepare_response = client.post("/vinilos/preparar")
    assert prepare_response.status_code == 200

    prepared_response = client.get("/vinilos/VIN-004")
    assert prepared_response.status_code == 200
    assert prepared_response.json()["tipo_articulo"] == (
        "Vinilo, LP, Unofficial Release, Picture Disc, Clock; Cofre"
    )


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
                "images": [
                    {"uri": "https://example.test/kind-front.jpg"},
                    {"uri": "https://example.test/kind-back.jpg"},
                    {"uri150": "https://example.test/kind-label.jpg"},
                ],
                "formats": [
                    {
                        "name": "Vinyl",
                        "qty": "2",
                        "descriptions": ["LP", "Album", "Stereo"],
                        "text": "Gatefold",
                    }
                ],
                "extraartists": [
                    {"name": "Miles Davis", "role": "Trumpet"},
                    {"name": "Bill Evans", "role": "Piano"},
                ],
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
    assert prepared_vinilo["tipo_articulo"] == "2 x Vinilo, LP, Album, Stereo, Gatefold"
    assert prepared_vinilo["duracion_total"] == "9:22"
    assert prepared_vinilo["estado_disco"] is None
    assert prepared_vinilo["estado_funda"] is None
    assert prepared_vinilo["comentarios_estado"] is None
    assert prepared_vinilo["estado_carga"] == "ALTA"
    assert prepared_vinilo["estado_tc"] is None
    assert prepared_vinilo["creditos"] == "Trumpet – Miles Davis\nPiano – Bill Evans"
    assert prepared_vinilo["tc_section"] is None

    update_response = client.put(
        "/vinilos/VIN-002",
        json={
            "tipo_articulo": "Vinilo, LP, Edición revisada",
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
            "creditos": "Trumpet – Miles Davis\nPiano – Bill Evans",
            "estado_disco": "VG+",
            "estado_funda": "VG",
            "comentarios_estado": "Ligero desgaste superficial, reproducción sólida.",
            "estado_tc": "4",
            "precio": 29.99,
            "estado_carga": "ALTA",
            "estado_stock": "En stock",
            "notas": "Edición <especial> & revisada\n\nSegundo párrafo.",
            "tc_section": "376",
        },
    )
    assert update_response.status_code == 200
    updated_vinilo = update_response.json()["vinilo"]
    assert updated_vinilo["nombre"] == "Kind of Blue"
    assert updated_vinilo["tipo_articulo"] == "Vinilo, LP, Edición revisada"
    assert updated_vinilo["estado_disco"] == "VG+"
    assert updated_vinilo["estado_funda"] == "VG"
    assert updated_vinilo["comentarios_estado"] == "Ligero desgaste superficial, reproducción sólida."
    assert updated_vinilo["estado_tc"] == "4"
    assert updated_vinilo["creditos"] == "Trumpet – Miles Davis\nPiano – Bill Evans"
    assert updated_vinilo["tc_section"] == "376"

    with duckdb.connect(str(tmp_path / "vinyls.duckdb")) as con:
        con.execute(
            """
            INSERT INTO items (
                id, product_type, title, artists, year,
                labels, country, total_duration, estimated_weight,
                genres, styles, media_condition, sleeve_condition, condition_comments,
                tc_condition,
                lowest_price, sale_price, listing_status, stock_status,
                tracklist, notes, updated_at
            )
            VALUES (
                'VIN-999', 'Vinilo, LP', 'Blue Train', 'John Coltrane', 1957,
                'Blue Note', 'US', '42:51', 180,
                'Jazz', 'Hard Bop', 'VG', 'VG', 'No debe salir en la exportación.',
                '3',
                18.00, 24.00, NULL, 'Vendido',
                'A1 - Blue Train (10:43)', 'Registro ya exportado', now()
            )
            """
        )
        con.execute(
            """
            INSERT INTO items (
                id, product_type, title, artists, year,
                labels, country, total_duration, estimated_weight,
                genres, styles, media_condition, sleeve_condition, condition_comments,
                tc_condition,
                lowest_price, sale_price, listing_status, stock_status,
                tracklist, notes, updated_at
            )
            VALUES (
                'VIN-777', 'Vinilo, LP', 'Giant Steps', 'John Coltrane', 1960,
                'Atlantic', 'US', '37:48', 180,
                'Jazz', 'Hard Bop', 'VG+', 'VG+', 'También exportable, pero no seleccionada.',
                '5',
                20.00, 26.00, 'CAMBIO', 'En stock',
                'A1 - Giant Steps (4:43)', 'Otra ficha exportable', now()
            )
            """
        )

    preview_response = client.get("/export/vinilos/preview")
    assert preview_response.status_code == 200
    preview_payload = preview_response.json()
    assert preview_payload["rows_count"] == 2
    assert set(preview_payload["ids"]) == {"VIN-002", "VIN-777"}

    export_response = client.post("/export/vinilos/csv", json={"ids": ["VIN-002"]})
    assert export_response.status_code == 200
    export_payload = export_response.json()
    assert export_payload["filename"].endswith(".csv")
    assert export_payload["rows"] == 1
    assert export_payload["ids"] == ["VIN-002"]

    download_response = client.get(
        "/export/vinilos/file",
        params={"filename": export_payload["filename"]},
    )
    assert download_response.status_code == 200
    header, *_ = download_response.text.splitlines()
    assert header.split("#") == _importamatic_template_columns()
    assert "Kind of Blue" in download_response.text
    assert "<p><strong>Formato:</strong> Vinilo, LP, Edición revisada</p>" in download_response.text
    assert "<p><strong>Tracklist:</strong></p><ul><li>A1 - So What (9:22)</li></ul>" in download_response.text
    assert (
        "<p><strong>Créditos:</strong></p><ul><li>Trumpet – Miles Davis</li>"
        "<li>Piano – Bill Evans</li></ul>"
        in download_response.text
    )
    assert "Edición &lt;especial&gt; &amp; revisada<br><br>Segundo párrafo." in download_response.text
    assert "29,99" in download_response.text
    assert "ALTA" in download_response.text
    assert "https://example.test/kind-front.jpg" not in download_response.text
    assert "#Otros#4,5" in download_response.text
    assert "Blue Train" not in download_response.text
    assert "Giant Steps" not in download_response.text

    clear_operation_response = client.post(
        "/export/vinilos/clear-operation",
        json={"ids": ["VIN-002"]},
    )
    assert clear_operation_response.status_code == 200
    assert clear_operation_response.json()["updated"] == 1
    assert clear_operation_response.json()["ids"] == ["VIN-002"]

    with duckdb.connect(str(tmp_path / "vinyls.duckdb")) as con:
        statuses = dict(
            con.execute(
                "SELECT id, listing_status FROM items WHERE id IN ('VIN-002', 'VIN-777')"
            ).fetchall()
        )
    assert statuses["VIN-002"] is None
    assert statuses["VIN-777"] == "CAMBIO"
