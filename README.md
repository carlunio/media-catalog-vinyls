# media-catalog-vinyls

Aplicación local para catalogar vinilos con `FastAPI`, `Streamlit` y `DuckDB`.

- Historial de cambios: `CHANGELOG.md`

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
make lint
make test
```

Notas:

- `make db-maint` ejecuta `CHECKPOINT` + `VACUUM` sobre la base actual.
- `make db-repack` genera una copia recompuesta más compacta como `*.repacked.duckdb`.
- `make db-repack-replace` sustituye la base activa por la recompuesta y guarda una copia `*.pre_repack.bak.duckdb`.
- Conviene parar backend y frontend antes de usar `db-repack-replace`.
- La base activa de la aplicación es `data/vinyls.duckdb`.

## Esquema DuckDB

- Tabla `discogs_release_payloads`: payload crudo de Discogs.
- Tabla `items`: catálogo editable de vinilos.
- Tabla `inventory_field_allowed_values`: valores cerrados usados por el formulario.
- Vista `export`: selección de campos en español para exportación, filtrada por `estado_carga` en `Para subir` y `Para actualizar`.

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
- `data/`: base de datos DuckDB local
- `data/exports/`: exportaciones generadas
- `docs/`: documentación Quarto
