## [Unreleased]

### Planned
- Definir flujo de releases estable para `main` y, si hace falta, canal paralelo `dev`.
- Añadir más contexto de versión en UI y operación cuando exista política cerrada de publicación.


## [0.2.0] - 2026-04-25

### Added
- Base de versionado visible en la aplicación con una única fuente de verdad compartida entre backend y frontend.
- `CHANGELOG.md` para documentar releases y cambios relevantes.
- Lanzadores multiplataforma en `tools/` para Windows (`.bat`) y Ubuntu/Linux (`.desktop` + `.sh`).
- `make update-repo` para actualizar explícitamente desde `origin main`.
- Tests mínimos de API para proteger flujos críticos.

### Changed
- `Makefile` actualizado para funcionar en Ubuntu y Windows con resolución de rutas consistente.
- Exportación desacoplada del filesystem compartido entre backend y frontend.
- Configuración centralizada de rutas y utilidades HTTP comunes en frontend.

### Fixed
- Corrección del flujo de sobrescritura en Discogs -> `vinilos_raw`.
- Validación y manejo de errores HTTP más fiables en backend y frontend.
- El backend ya no falla al arrancar solo por faltar `DISCOGS_TOKEN` si no se usa Discogs.
- Limpieza de artefactos Python generados que estaban versionados por error.


## [0.1.0] - 2026-04-24

Primera versión funcional del catálogo de vinilos con:

- backend FastAPI
- frontend Streamlit multipágina
- persistencia en DuckDB
- búsqueda de releases en Discogs
- revisión manual y exportación tabulada
