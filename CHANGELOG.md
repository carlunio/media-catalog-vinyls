## [Unreleased]

### Planned
- Definir flujo de releases estable para `main` y, si hace falta, canal paralelo `dev`.
- Añadir más contexto de versión en UI y operación cuando exista política cerrada de publicación.

### Changed
- La carpeta de exportación pasa a ser `data/exports` en vez de `exports`, quedando todo `data/` como contenido local ignorado por git.
- `estado_conservacion` pasa a usar grados estilo Discogs (`M`, `NM`, `VG+`, etc.), con valor por defecto nulo y nuevo campo `detalle_estado_conservacion`.
- Los campos cerrados de `vinilos` pasan a gestionarse con tabla de valores permitidos en DuckDB y endpoint de opciones, siguiendo el patrón aplicado en `media-catalog-books`.
- `vinilos_raw` pasa a persistir el payload crudo en una columna `data` de tipo `JSON` real en DuckDB, con migración suave para tablas antiguas.
- La migración de `vinilos_raw` elimina físicamente la antigua columna `raw_json` tras copiar su contenido a `data`, de modo que el esquema activo ya no arrastra campos legacy.
- Se añaden utilidades de mantenimiento de DuckDB (`db-maint`, `db-repack`, `db-repack-replace`) siguiendo el patrón ya aplicado en `media-catalog-books`.
- El esquema interno de DuckDB pasa a nombres de tabla y columna en inglés estandarizado, manteniendo la API y la UI actuales en español como capa de compatibilidad.
- La exportación pasa a apoyarse en la vista DuckDB `export`, con cabeceras Importamatic separadas por `#` y filtro por `estado_carga` en `ALTA`, `CAMBIO` y `BAJA`.
- Se añade `estado_tc` editable con valores 1-5 y la descripción de estado exportada se compone desde disco, funda y comentarios de conservación.
- La pantalla de revisión manual se reorganiza con una cabecera funcional (`id`, tipo y estados), bloques semánticos y etiquetas cromáticas inspiradas en el formulario de `media-catalog-books`.
- La revisión manual gana una presentación más limpia y utilizable, con selector más informativo, tarjetas visuales y un campo amplio para detallar el estado de conservación.
- `duracion_total` pasa a calcularse automáticamente desde las duraciones individuales de la `tracklist`, devolviendo `mm:ss` o `h:mm:ss` según corresponda.
- La integración con Discogs pasa a mostrar mensajes específicos por código de respuesta HTTP en búsqueda y carga de releases, en vez de un error genérico.


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
