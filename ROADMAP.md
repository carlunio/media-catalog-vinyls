# Hoja de ruta

Hoja de ruta viva para `media-catalog-vinyls`.

Este documento recoge la dirección técnica del proyecto, las prioridades de producto y las decisiones pendientes para convertir la aplicación en una versión local estable, mantenible y publicable mediante releases.

La intención es que sea un documento de consulta: se puede completar, recortar, reordenar o marcar como hecho a medida que el proyecto avance.

## Objetivo del proyecto

`media-catalog-vinyls` debe ser una aplicación local fiable para catalogar vinilos, enriquecer fichas desde Discogs, revisarlas manualmente y exportarlas en formato compatible con Importamatic de Todocolección.

El objetivo principal no es convertirla inmediatamente en un SaaS ni en una aplicación web multiusuario. El primer objetivo de producción es más concreto:

- Que una persona pueda instalar una versión concreta.
- Que pueda actualizar solo a versiones estables.
- Que sus datos locales no se pierdan durante una actualización.
- Que cada release sea reproducible, probada y documentada.
- Que el código pueda seguir creciendo sin concentrar demasiadas responsabilidades en un único módulo.

## Estado actual

Versión preparada: `1.0.0`.

Arquitectura actual:

```text
Usuario
  -> Streamlit
      -> FastAPI
          -> DuckDB
          -> Discogs
```

Fortalezas actuales:

- Separación práctica entre frontend Streamlit y backend FastAPI.
- Persistencia local sencilla con DuckDB.
- Datos locales fuera de Git mediante `data/` y ficheros `.duckdb` ignorados.
- Versión visible desde una única fuente en `pyproject.toml`.
- `CHANGELOG.md` ya iniciado.
- Tests de API que cubren flujos importantes: ingesta de datos crudos, preparación, revisión, exportación y errores de Discogs.
- Comandos `make` para instalación, ejecución, actualización, lint, tests y mantenimiento de DuckDB.

Limitaciones actuales:

- La aplicación está pensada para uso local de un único usuario.
- La API no tiene autenticación.
- Las tablas se crean y sincronizan al importar el backend.
- No hay migraciones versionadas explícitas.
- No hay CI/CD en GitHub Actions.
- Las dependencias no están bloqueadas con un lockfile.
- `make update-repo` sigue `main`, no la última release estable.
- La lógica de dominio, migración, exportación y normalización está muy concentrada en `src/backend/services/vinilos.py`.

## Principios de trabajo

Estos principios deben guiar las decisiones técnicas:

- Datos primero: ningún cambio debe poner en riesgo `data/vinyls.duckdb`.
- Releases verificadas: no se publica una tag si `make lint` o `make test` fallan.
- Actualizaciones reversibles: antes de migraciones destructivas debe existir backup.
- Producción local antes que multiusuario: endurecer bien el caso local antes de abrir red, usuarios o despliegues remotos.
- Contratos claros: la API debe validar reglas de negocio, no delegarlas solo en el frontend.
- Cambios pequeños y verificables: cada hito debe poder probarse con criterios concretos.
- Documentación operativa: cada mecanismo de release, backup, migración y actualización debe quedar descrito.

## Leyenda

Prioridad:

- `P0`: bloquea release o puede causar pérdida de datos.
- `P1`: necesario para producción local estable.
- `P2`: mejora importante de mantenibilidad, seguridad o experiencia.
- `P3`: deseable, puede esperar.

Estado:

- `[ ]`: pendiente.
- `[~]`: en progreso.
- `[x]`: completado.
- `[?]`: necesita decisión.

## Hitos

### M0. Cierre de `v1.0.0`

Objetivo: publicar una primera versión estable, local y documentada.

Alcance:

- Congelar el estado actual como release `v1.0.0`.
- Asegurar que la versión declarada, los tests y el changelog coinciden.
- Publicar tag y release en GitHub.

Tareas:

- [ ] `P0` Actualizar el test de versión para que espere `1.0.0`.
- [ ] `P0` Ejecutar `make lint`.
- [ ] `P0` Ejecutar `make test`.
- [ ] `P0` Revisar que `CHANGELOG.md` tenga sección `1.0.0`.
- [ ] `P1` Confirmar que `README.md` explica instalación, ejecución y comandos principales.
- [ ] `P1` Crear commit de release: `Prepare release v1.0.0`.
- [ ] `P1` Crear tag anotada: `v1.0.0`.
- [ ] `P1` Publicar GitHub Release con notas basadas en `CHANGELOG.md`.

Criterios de aceptación:

- `make lint` pasa.
- `make test` pasa.
- `pyproject.toml`, UI/backend y test de metadatos reportan `1.0.0`.
- La tag `v1.0.0` apunta al commit que contiene `CHANGELOG.md` y `pyproject.toml` actualizados.
- El release de GitHub explica que esta versión está orientada a producción local, no a despliegue web multiusuario.

### M1. Producción local estable

Objetivo: que una persona pueda usar y actualizar la aplicación sin exponerse a cambios a medio hacer.

Alcance:

- Definir canal estable.
- Separar actualización desde `main` y actualización a release estable.
- Incorporar backups operativos de la base local.
- Mejorar instrucciones para usuarios no técnicos.

Tareas:

- [ ] `P1` Decidir si existirá rama `stable`.
- [ ] `P1` Crear `make update-stable` si se adopta rama `stable`.
- [ ] `P1` Crear `make update-release` si se adopta actualización por tag.
- [ ] `P1` Documentar diferencia entre `main`, `stable` y tags `v*`.
- [ ] `P0` Crear `make backup-db`.
- [ ] `P1` Crear `make restore-db`.
- [ ] `P1` Documentar procedimiento antes de actualizar: parar app, backup, actualizar, arrancar, verificar.
- [ ] `P2` Mostrar en la UI canal y versión: por ejemplo `1.0.0`, `1.0.1`, `1.1.0 (dev)`.
- [ ] `P2` Añadir una pantalla o bloque de diagnóstico local: versión, ruta DB, ruta exports y estado backend.

Criterios de aceptación:

- Un usuario puede instalar `v1.0.0` o actualizar a una release concreta sin seguir automáticamente `main`.
- Existe un backup manual documentado y probado.
- El README explica qué comando usar según el perfil: desarrollo o usuario estable.
- La ruta de datos local queda clara.

### M2. Migraciones y seguridad de datos

Objetivo: que los cambios de esquema de DuckDB sean explícitos, auditables y reversibles.

Alcance:

- Sustituir sincronizaciones implícitas por migraciones versionadas.
- Evitar modificaciones destructivas en arranque sin control.
- Proteger especialmente `tc_sections`, `items` y `discogs_release_payloads`.

Tareas:

- [ ] `P0` Crear tabla `schema_migrations`.
- [ ] `P1` Crear carpeta `src/backend/migrations`.
- [ ] `P1` Mover creación inicial de tablas a migraciones numeradas.
- [ ] `P1` Crear comando `make migrate-db`.
- [ ] `P1` Hacer que el backend verifique migraciones pendientes al arrancar.
- [ ] `P1` Definir política: aplicar migraciones automáticamente o exigir comando manual.
- [ ] `P0` Antes de migraciones destructivas, exigir backup o crear backup automático.
- [ ] `P0` Cambiar sincronización de `tc_sections`: no borrar tabla activa si el CSV falta o se parsea vacío.
- [ ] `P1` Añadir pruebas de migración desde una DB antigua simulada.
- [ ] `P2` Registrar versión de app que creó o migró la DB.

Criterios de aceptación:

- Una DB creada con una versión anterior puede abrirse con la nueva versión mediante un camino probado.
- Las migraciones son idempotentes o tienen control claro de ejecución única.
- Si falta `data/secciones.csv`, no se destruye el catálogo de secciones ya existente.
- Cada migración relevante queda cubierta por tests.

### M2.5. Sincronización por snapshots en carpeta compartida

Objetivo: permitir que dos personas coordinadas intercambien el estado de la base DuckDB usando una carpeta sincronizada en la nube, sin abrir la base viva directamente desde esa carpeta.

Principio de diseño:

```text
data/vinyls.duckdb
  -> base local de trabajo

carpeta sincronizada/snapshots/
  -> copias cerradas, reempaquetadas e inmutables
```

La carpeta compartida no debe comportarse como una base de datos desplegada. Debe comportarse como un almacén de snapshots. La aplicación nunca debe escribir directamente sobre una DuckDB viva dentro de Dropbox, Drive, OneDrive, Syncthing o equivalente.

Alcance:

- Publicar snapshots de la DB local en una carpeta sincronizada.
- Detectar snapshots más recientes al abrir la app.
- Ofrecer importación manual, nunca automática.
- Crear backup local obligatorio antes de importar un snapshot externo.
- Mantener solo un histórico razonable de snapshots.

Configuración prevista:

- `CLOUD_SNAPSHOTS_DIR`: ruta local de la carpeta sincronizada.
- `SYNC_ACTOR`: nombre corto de la persona que publica el snapshot, por ejemplo `carlos` o `dani`.
- `SYNC_DEVICE`: identificador corto del equipo, por ejemplo `thinkpad-carlos`.
- `SYNC_RETENTION_DAYS`: días de retención, por defecto `14`.
- `SYNC_KEEP_MIN`: mínimo de snapshots a conservar aunque superen la retención, por ejemplo `10`.

Estructura propuesta:

```text
data/
  vinyls.duckdb
  backups/
    local/
      vinyls_before_import_20260530_192200.duckdb
  sync_state.json

CarpetaNube/
  media-catalog-vinyls/
    snapshots/
      vinyls_20260530_183012_carlos_thinkpad.duckdb
      vinyls_20260530_183012_carlos_thinkpad.json
      vinyls_20260530_191455_dani_sobremesa.duckdb
      vinyls_20260530_191455_dani_sobremesa.json
```

Manifiesto de snapshot:

```json
{
  "snapshot_id": "20260530_183012_carlos_thinkpad",
  "created_at": "2026-05-30T18:30:12+02:00",
  "app_version": "1.0.0",
  "schema_version": "1",
  "source_actor": "carlos",
  "source_device": "thinkpad",
  "db_filename": "vinyls_20260530_183012_carlos_thinkpad.duckdb",
  "db_size_bytes": 12345678,
  "sha256": "...",
  "protected": false,
  "notes": "Snapshot manual desde la app"
}
```

Estado local de sincronización:

```json
{
  "last_imported_snapshot_id": "20260530_183012_carlos_thinkpad",
  "last_imported_sha256": "...",
  "last_published_snapshot_id": "20260530_183012_carlos_thinkpad",
  "last_sync_at": "2026-05-30T18:31:00+02:00"
}
```

Flujo para publicar snapshot:

1. La app termina cualquier operación pendiente.
2. DuckDB ejecuta `CHECKPOINT`.
3. Se crea una copia reempaquetada en una ruta temporal mediante el mismo principio que `db-repack`.
4. Se calcula `sha256` de la copia reempaquetada.
5. Se copia el `.duckdb` final a `CLOUD_SNAPSHOTS_DIR/snapshots`.
6. Se escribe el manifiesto `.json` al final, solo cuando la copia está completa.
7. Se actualiza `data/sync_state.json`.
8. Se ejecuta limpieza de snapshots antiguos según política de retención.

Flujo para detectar snapshot externo:

1. Al abrir la app, se listan manifiestos `.json` válidos.
2. Se ignoran snapshots sin `.duckdb`, con hash incorrecto o manifiesto incompleto.
3. Se localiza el snapshot válido más reciente.
4. Si es más reciente que el último importado o publicado, la UI muestra aviso.
5. La app ofrece ver detalles, ignorar, publicar primero los cambios locales o importar.

Flujo para importar snapshot:

1. La importación nunca es automática.
2. La UI muestra quién lo publicó, cuándo, versión de app, tamaño y hash.
3. Antes de importar, se crea backup local obligatorio de `data/vinyls.duckdb`.
4. Se verifica `sha256` del snapshot.
5. Se reemplaza la DB local solo si la verificación pasa.
6. Se actualiza `data/sync_state.json`.
7. Se recomienda reiniciar backend/frontend si la DB estaba abierta.

Casos de conflicto funcional:

- Si la DB local no coincide con el último snapshot importado y existe un snapshot externo más nuevo, la app debe avisar de posible conflicto.
- Si el snapshot más nuevo fue publicado por el mismo `SYNC_ACTOR` y `SYNC_DEVICE`, se puede tratar como ya conocido o como copia propia.
- Si hay cambios locales no publicados, la app debe ofrecer publicar snapshot local antes de importar el externo.

Tareas:

- [ ] `P1` Añadir variables `CLOUD_SNAPSHOTS_DIR`, `SYNC_ACTOR`, `SYNC_DEVICE`, `SYNC_RETENTION_DAYS` y `SYNC_KEEP_MIN`.
- [ ] `P1` Crear módulo de sincronización por snapshots, por ejemplo `src/backend/services/snapshots.py`.
- [ ] `P1` Crear generación de snapshot reempaquetado sin modificar la DB activa.
- [ ] `P1` Calcular y guardar `sha256`.
- [ ] `P1` Escribir manifiesto `.json` solo después de copiar la DB completa.
- [ ] `P1` Crear lectura y validación de manifiestos.
- [ ] `P1` Crear `data/sync_state.json` o tabla interna equivalente.
- [ ] `P1` Detectar al arrancar si existe un snapshot externo más reciente.
- [ ] `P1` Crear backup local obligatorio antes de importar.
- [ ] `P1` Implementar importación manual desde snapshot verificado.
- [ ] `P1` Implementar limpieza automática de snapshots antiguos.
- [ ] `P1` Conservar siempre al menos `SYNC_KEEP_MIN` snapshots.
- [ ] `P1` Conservar siempre el último snapshot de cada actor/dispositivo.
- [ ] `P2` Permitir snapshots protegidos que no se borren en limpieza automática.
- [ ] `P2` Añadir comandos `make publish-snapshot`, `make import-snapshot`, `make list-snapshots` y `make cleanup-snapshots`.
- [ ] `P2` Añadir pantalla Streamlit "Datos" o "Sistema" con publicar, importar, listar y limpiar snapshots.
- [ ] `P2` Documentar el protocolo de uso entre dos personas.
- [ ] `P2` Añadir tests con snapshots válidos, incompletos, corruptos y antiguos.

Criterios de aceptación:

- La app nunca abre en escritura una DuckDB ubicada directamente en la carpeta sincronizada.
- Publicar snapshot genera `.duckdb` reempaquetado y `.json` coherente.
- Un snapshot a medio sincronizar se ignora hasta que el manifiesto y el hash sean válidos.
- Importar crea backup local antes de reemplazar la DB.
- La importación requiere confirmación explícita.
- La limpieza elimina snapshots antiguos sin borrar los protegidos, los mínimos conservados ni el último de cada actor/dispositivo.
- El README o la documentación explican claramente que la nube es un almacén de snapshots, no una base de datos compartida.

### M3. Calidad, CI y releases reproducibles

Objetivo: que la calidad no dependa de recordar comandos manuales.

Alcance:

- GitHub Actions para lint y tests.
- Política de release automatizable.
- Dependencias reproducibles.

Tareas:

- [ ] `P1` Crear workflow `.github/workflows/ci.yml`.
- [ ] `P1` Ejecutar lint en CI.
- [ ] `P1` Ejecutar tests en CI.
- [ ] `P1` Ejecutar CI en pull requests y pushes a `main`.
- [ ] `P1` Ejecutar CI en tags `v*`.
- [ ] `P2` Crear workflow de release que genere notas o assets al publicar tag.
- [ ] `P1` Decidir herramienta de lockfile: `uv`, `pip-tools` u otra.
- [ ] `P1` Generar lockfile para dependencias exactas.
- [ ] `P2` Separar dependencias de ejecución y desarrollo.
- [ ] `P2` Añadir una prueba mínima importando el backend sin `DISCOGS_TOKEN`.
- [ ] `P2` Añadir tests para scripts de backup/migración.

Criterios de aceptación:

- GitHub muestra estado verde antes de mergear o publicar release.
- Un checkout de una tag instala dependencias equivalentes en el futuro.
- La publicación de tags no depende solo de disciplina manual.

### M4. Modularización del backend

Objetivo: reducir acoplamiento y facilitar nuevas funcionalidades sin agrandar `vinilos.py`.

Problema actual:

`src/backend/services/vinilos.py` contiene varias responsabilidades:

- Constantes de dominio.
- Mapeos API <-> DB.
- Normalización de Discogs.
- Construcción de secciones Todocolección.
- Migraciones suaves.
- SQL de exportación.
- CRUD de items.
- Reglas de estado y exportabilidad.

Arquitectura propuesta:

```text
src/backend/
  api/
    routes_discogs.py
    routes_items.py
    routes_exports.py
    routes_health.py
  domain/
    items.py
    discogs_mapping.py
    importamatic.py
    todocoleccion_sections.py
  repositories/
    items_repo.py
    raw_payloads_repo.py
    allowed_values_repo.py
    tc_sections_repo.py
  services/
    catalog_service.py
    export_service.py
    discogs_service.py
  migrations/
  database.py
  config.py
```

Tareas:

- [ ] `P2` Extraer transformaciones Discogs -> item a `domain/discogs_mapping.py`.
- [ ] `P2` Extraer lógica de duración, créditos y formato a funciones puras testeables.
- [ ] `P2` Extraer construcción de export Importamatic a `domain/importamatic.py`.
- [ ] `P2` Extraer SQL de items a `repositories/items_repo.py`.
- [ ] `P2` Extraer SQL de payloads crudos a `repositories/raw_payloads_repo.py`.
- [ ] `P2` Separar routers FastAPI por área funcional.
- [ ] `P2` Mantener compatibilidad de endpoints existentes durante la refactorización.
- [ ] `P2` Añadir tests unitarios de dominio sin arrancar FastAPI.

Criterios de aceptación:

- `vinilos.py` deja de ser el centro de todas las responsabilidades.
- Las reglas de negocio principales pueden probarse sin DuckDB y sin FastAPI.
- Los endpoints públicos siguen respondiendo igual.

### M5. Contratos de API y validación

Objetivo: que el backend sea el guardián real de las reglas de negocio.

Alcance:

- Validaciones Pydantic más estrictas.
- Errores consistentes.
- Endpoints más semánticos.

Tareas:

- [ ] `P1` Validar `estado_carga` contra `ALTA`, `CAMBIO`, `BAJA` o nulo.
- [ ] `P1` Validar `estado_stock` contra valores permitidos.
- [ ] `P1` Validar `estado_disco` y `estado_funda` contra escala permitida.
- [ ] `P1` Validar `estado_tc` contra `1`, `2`, `3`, `4`, `5` o nulo.
- [ ] `P1` Validar `precio` y `estimated_weight` como no negativos.
- [ ] `P2` Normalizar respuestas de error con una estructura única: `title`, `message`, `hint`, `status_code`.
- [ ] `P2` Cambiar export con efectos secundarios de `GET` a `POST`.
- [ ] `P2` Introducir ids de exportación: `POST /export/vinilos` y `GET /export/vinilos/{export_id}/file`.
- [ ] `P3` Versionar API si aparecen cambios incompatibles: `/api/v1/...`.

Criterios de aceptación:

- Una petición inválida desde fuera de Streamlit no puede dejar datos incoherentes.
- Los errores son comprensibles para UI y para depuración.
- Los endpoints respetan mejor la semántica HTTP.

### M6. Seguridad y exposición en red

Objetivo: dejar claro que la app local no debe exponerse sin controles.

Alcance:

- Seguridad mínima para entorno local.
- Seguridad necesaria si se abre a red local o internet.

Tareas:

- [ ] `P1` Documentar oficialmente que la configuración por defecto es local.
- [ ] `P1` Asegurar que backend y frontend arrancan ligados a `127.0.0.1` salvo configuración explícita.
- [ ] `P1` Añadir token interno opcional entre Streamlit y FastAPI.
- [ ] `P2` Ocultar rutas sensibles o de mantenimiento si no hay token.
- [ ] `P2` Revisar CORS si se expone la API.
- [ ] `P2` Documentar requisitos para exponer en LAN: firewall, token, backup.
- [ ] `P3` Evaluar autenticación real si hay múltiples usuarios.
- [ ] `P3` Evaluar HTTPS o reverse proxy si sale de localhost.

Criterios de aceptación:

- Un usuario entiende la diferencia entre uso local y uso expuesto.
- La API no queda accidentalmente abierta sin aviso.
- Hay un camino mínimo de autenticación para usos fuera de `localhost`.

### M7. Operación, observabilidad y soporte

Objetivo: poder diagnosticar problemas sin abrir el código.

Alcance:

- Logs.
- Healthchecks.
- Diagnóstico local.
- Scripts de mantenimiento seguros.

Tareas:

- [ ] `P2` Mejorar `/health` para incluir versión y estado DB.
- [ ] `P2` Crear `/health/details` o endpoint de diagnóstico local protegido si se añade token.
- [ ] `P2` Configurar logging estructurado básico en backend.
- [ ] `P2` Registrar errores de Discogs con contexto no sensible.
- [ ] `P2` Registrar exports generados: fecha, filename, ids, número de filas.
- [ ] `P2` Añadir comando `make doctor`.
- [ ] `P2` Añadir comando `make version`.
- [ ] `P3` Añadir pantalla Streamlit "Sistema" con estado de versión, backend, DB y rutas.

Criterios de aceptación:

- Ante un fallo de usuario, se puede pedir versión, ruta DB y último error de forma simple.
- Los logs ayudan sin exponer `DISCOGS_TOKEN`.
- Los comandos operativos tienen salidas comprensibles.

### M8. Frontend y experiencia de usuario

Objetivo: mantener Streamlit como herramienta eficiente de trabajo repetido.

Alcance:

- Mejoras de usabilidad sin perder densidad.
- Estados claros.
- Menos dependencia de conocimiento implícito.

Tareas:

- [ ] `P2` Mostrar versión y canal con más contexto en sidebar.
- [ ] `P2` Mostrar estado de backend sin bloquear demasiado cada página.
- [ ] `P2` Añadir confirmaciones explícitas en acciones destructivas o masivas.
- [ ] `P2` Mejorar mensajes de error de API en revisión y exportación.
- [ ] `P2` Añadir filtros en revisión: pendientes de precio, pendientes de estado, listos para exportar.
- [ ] `P2` Añadir búsqueda por id, artista o título en revisión.
- [ ] `P3` Mantener una página de ayuda operativa mínima dentro de la app.

Criterios de aceptación:

- Revisar muchos vinilos seguidos sigue siendo rápido.
- El usuario ve por qué una ficha entra o no entra en exportación.
- Las acciones importantes tienen feedback claro.

### M9. Documentación

Objetivo: que el proyecto se pueda retomar en el futuro sin reconstruir contexto mental.

Tareas:

- [ ] `P1` Completar README con flujo de release.
- [ ] `P1` Documentar backup y restore.
- [ ] `P1` Documentar actualización estable.
- [ ] `P1` Documentar migraciones cuando existan.
- [ ] `P2` Crear `docs/architecture.md` o página Quarto equivalente.
- [ ] `P2` Crear `docs/operations.md`.
- [ ] `P2` Crear `docs/release-process.md`.
- [ ] `P2` Mantener `CHANGELOG.md` por versión.
- [ ] `P2` Mantener este `ROADMAP.md` como documento vivo.

Criterios de aceptación:

- Una persona puede instalar, arrancar, actualizar, respaldar y publicar una release siguiendo docs.
- Las decisiones importantes quedan reflejadas en documentos editables.

## Backlog por área

### Versionado y releases

- [ ] Crear política SemVer: `MAJOR.MINOR.PATCH`.
- [ ] Usar pre-releases para pruebas: `v1.1.0-rc.1`.
- [ ] Automatizar notas de release desde `CHANGELOG.md` o commits.
- [ ] Mantener rama `stable` si hay usuarios no técnicos.
- [ ] Documentar rollback a tag anterior.

### Datos

- [ ] Backup antes de migrar.
- [ ] Restore probado.
- [ ] Migraciones versionadas.
- [ ] Registro de versión de esquema.
- [ ] Validación de integridad de DB.
- [ ] Evitar borrados completos si falla una fuente auxiliar como `secciones.csv`.
- [ ] Publicación de snapshots reempaquetados en carpeta sincronizada.
- [ ] Importación manual desde snapshot verificado.
- [ ] Estado local de sincronización mediante `sync_state.json` o tabla equivalente.
- [ ] Limpieza automática de snapshots antiguos con retención mínima.

### Backend

- [ ] Routers por dominio.
- [ ] Repositorios por tabla.
- [ ] Servicios por caso de uso.
- [ ] Funciones puras para mapeos y exportación.
- [ ] Validadores Pydantic de reglas de negocio.
- [ ] Errores coherentes.

### Frontend

- [ ] Diagnóstico local.
- [ ] Pantalla para publicar, importar y listar snapshots.
- [ ] Aviso al detectar snapshot externo más reciente.
- [ ] Filtros y búsqueda en revisión.
- [ ] Mejor estado de carga y errores.
- [ ] Confirmaciones para acciones sensibles.
- [ ] Menos llamadas repetidas si el backend no está disponible.

### Operación

- [ ] CI.
- [ ] Lockfile.
- [ ] Backup/restore.
- [ ] Comandos de snapshots: publicar, importar, listar y limpiar.
- [ ] Comando de diagnóstico.
- [ ] Logs.
- [ ] Healthcheck ampliado.

### Seguridad

- [ ] Token interno.
- [ ] Bind local por defecto.
- [ ] Avisos para exposición en red.
- [ ] CORS controlado.
- [ ] Autenticación real si aparece uso multiusuario.

## Riesgos

| Riesgo | Impacto | Mitigación |
| --- | --- | --- |
| Migración rompe `data/vinyls.duckdb` | Alto | Backup previo, migraciones probadas, restore documentado |
| Usuarios actualizan desde `main` por error | Medio/alto | Rama `stable`, `make update-stable`, docs claras |
| Dependencias cambian tras una tag | Medio | Lockfile y CI por release |
| API expuesta en red sin autenticación | Alto | Bind local, token, documentación de seguridad |
| `vinilos.py` crece demasiado | Medio | Modularización por dominio/repositorio/servicio |
| `secciones.csv` falta o cambia formato | Medio | Validación antes de reemplazar tabla, tests con fixture |
| Export generado con datos incompletos | Medio | Validaciones, preview clara, tests de exportación |
| Sincronización de nube copia un snapshot incompleto | Medio/alto | Manifiesto escrito al final, hash `sha256`, ignorar snapshots inválidos |
| Dos personas publican snapshots divergentes | Medio | `SYNC_ACTOR`, `SYNC_DEVICE`, `sync_state`, aviso de conflicto e importación manual |
| Limpieza automática borra demasiado historial | Medio | Retención mínima, último snapshot por actor/dispositivo y snapshots protegidos |

## Decisiones Pendientes

- [?] Usar rama `stable` o solo tags para usuarios finales.
- [?] Elegir herramienta de lockfile: `uv`, `pip-tools` u otra.
- [?] Aplicar migraciones automáticamente al arrancar o mediante comando manual.
- [?] Mantener DuckDB como única base para siempre o prever migración a PostgreSQL si aparece uso multiusuario.
- [?] Añadir autenticación mínima ahora o esperar hasta que se exponga fuera de localhost.
- [?] Usar `sync_state.json` o una tabla interna para registrar el estado de snapshots.
- [?] Definir si la detección de snapshot externo ocurre al arrancar backend, al abrir Streamlit o mediante botón manual.
- [?] Decidir si el repack de snapshot reutiliza `scripts/db_maintenance.py` o vive en un servicio nuevo específico.

## Definición de hecho para releases

Una release se considera lista cuando:

- [ ] `pyproject.toml` tiene la versión final.
- [ ] `CHANGELOG.md` tiene entrada fechada.
- [ ] `ROADMAP.md` se revisó si el release cambia prioridades.
- [ ] `make lint` pasa.
- [ ] `make test` pasa.
- [ ] Si hay migración, existe backup recomendado y test de migración.
- [ ] Si cambia el protocolo de snapshots, existe prueba de publicación/importación y documentación actualizada.
- [ ] README o docs explican cualquier cambio operativo.
- [ ] La tag anotada se crea desde el commit correcto.
- [ ] El GitHub Release se publica con notas claras.

## Propuesta de orden inmediato

1. Corregir test de versión `1.0.0`.
2. Ejecutar lint y tests.
3. Publicar `v1.0.0`.
4. Añadir backup/restore.
5. Añadir sincronización por snapshots en carpeta compartida.
6. Crear CI básico.
7. Definir actualización estable.
8. Introducir migraciones.
9. Modularizar backend.
