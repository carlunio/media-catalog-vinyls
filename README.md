# media-catalog-vinyls

Aplicación local para catalogar vinilos con `FastAPI`, `Streamlit` y `DuckDB`.

Puedes consultar:

- Historial de cambios: [`CHANGELOG.md`](./CHANGELOG.md)
- Hoja de ruta: [`ROADMAP.md`](./ROADMAP.md)
  
## Requisitos

- Python 3.12+
- Un token de Discogs para usar la búsqueda y la descarga de releases

## Configuración

1. Crea tu entorno a partir del ejemplo:

```bash
cp .env.example .env
```

2. Ajusta al menos `DISCOGS_TOKEN`.

## Puesta en marcha

```bash
make setup
make dev
```

Servicios por defecto:

- Backend: `http://127.0.0.1:8000`
- Frontend: `http://127.0.0.1:8501`

## Comandos útiles

```bash
make dev
make stop
make restart
make update-repo
make update
make db-maint
make db-repack
make db-repack-replace
make publish-snapshot
make list-snapshots
make import-snapshot SNAPSHOT_ID=...
make cleanup-snapshots
make lint
make test
```

Notas:

- `make db-maint` ejecuta `CHECKPOINT` + `VACUUM` sobre la base actual.
- `make db-repack` genera una copia recompuesta más compacta como `*.repacked.duckdb`.
- `make db-repack-replace` sustituye la base activa por la recompuesta y guarda una copia `*.pre_repack.bak.duckdb`.
- Conviene parar backend y frontend antes de usar `db-repack-replace`.
- La base activa de la aplicación es `data/vinyls.duckdb`.
- La carpeta externa de snapshots se configura con `CLOUD_SNAPSHOTS_DIR`; por defecto apunta a `../bbdd/media-catalog-vinyls`, fuera del proyecto.
- `make publish-snapshot` publica una copia reempaquetada de la base local en `CLOUD_SNAPSHOTS_DIR/snapshots`, con manifiesto JSON y `sha256`.
- `make list-snapshots` lista los snapshots disponibles y `make cleanup-snapshots` aplica la retención configurada por `SYNC_RETENTION_DAYS` y `SYNC_KEEP_MIN`.
- `make import-snapshot SNAPSHOT_ID=...` importa manualmente un snapshot verificado y crea antes un backup local en `data/backups/local`.
- `data/secciones.csv` es el catálogo local de secciones de Todocolección; se usa para poblar `tc_sections` y el selector de sección TC.
- La [guía de uso de Importamatic de Todocolección](https://www.todocoleccion.net/mitc/vendedor/guia-de-uso-importamatic) es la referencia para obtener `secciones.csv`, las plantillas de Importamatic y la información de valores admitidos en algunos campos.

## Esquema DuckDB

- Tabla `discogs_release_payloads`: datos originales de Discogs.
- Tabla `items`: catálogo editable de vinilos.
- Tabla `inventory_field_allowed_values`: valores cerrados usados por el formulario.
- Tabla `tc_sections`: árbol de secciones de Todocolección generado desde `data/secciones.csv`.
- Vista `export`: plantilla Importamatic `Otros` separada por `#`, filtrada por `estado_carga` en `ALTA`, `CAMBIO` y `BAJA`, con `GASTOS FIJOS` configurable mediante `IMPORTAMATIC_OTHERS_FIXED_COST`.

## Versionado

- La versión publicada vive en `pyproject.toml`.
- El frontend y el backend leen esa misma versión, así que se muestran sincronizados.
- El historial de cambios se documenta en `CHANGELOG.md`.

Para publicar una nueva versión:

1. Cambia `project.version` en `pyproject.toml`.
2. Añade una nueva entrada en `CHANGELOG.md`.
3. Publica esos cambios en `main`.

Si más adelante quieres distinguir entornos paralelos, puedes usar opcionalmente `APP_CHANNEL=dev` para que la UI muestre algo como `0.2.0 (dev)` sin romper el versionado base.

## Estructura

- `src/backend`: API, acceso a datos y lógica de negocio
- `src/frontend`: interfaz de Streamlit
- `data/`: base de datos DuckDB local y CSV auxiliares locales
- `data/exports/`: exportaciones generadas
- `docs/`: documentación Quarto
