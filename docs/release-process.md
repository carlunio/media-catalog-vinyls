# Proceso de tags y releases en GitHub

Guía práctica para publicar una nueva versión de `media-catalog-vinyls` con un flujo sencillo, reproducible y seguro.

## Objetivo

El objetivo es que cada release:

- tenga una versión clara y coherente;
- apunte a un commit concreto y verificable;
- quede documentada en `CHANGELOG.md`;
- se pueda reconstruir y revisar más adelante;
- no requiera mover tags ya publicadas.

## Convenciones

- Versionado: `MAJOR.MINOR.PATCH`, por ejemplo `1.0.0`.
- Nombre de la tag: siempre con prefijo `v`, por ejemplo `v1.0.0`.
- Tipo de tag: anotada, no ligera.
- Rama de salida recomendada: `main`, salvo que en el futuro exista una rama estable específica.
- Mensaje de commit de preparación recomendado: `Prepare release vX.Y.Z`.
- Título del release en GitHub: `vX.Y.Z`.

Para versiones de prueba:

- usar pre-releases, por ejemplo `v1.1.0-rc.1`;
- marcar el release como pre-release en GitHub;
- no marcarlo como última versión estable.

## Antes de crear la tag

1. Asegúrate de estar en una rama limpia:

```bash
git status
```

2. Sitúate en `main` y trae el último estado sin crear merges innecesarios:

```bash
git switch main
git pull --ff-only origin main
```

3. Actualiza los archivos de versión y documentación que correspondan:

- `pyproject.toml`
- `CHANGELOG.md`
- `ROADMAP.md`, si la release cambia prioridades o cierra hitos
- cualquier otra documentación operativa afectada

4. Revisa que el `CHANGELOG.md` tenga:

- fecha correcta;
- cambios agrupados con claridad;
- ortografía y nombres de ficheros correctos;
- solo cambios realmente incluidos en la release.

5. Ejecuta las comprobaciones del proyecto:

```bash
make lint
make test
```

Si algo falla, no crees la tag todavía.

## Preparar el commit de release

Añade solo los cambios que deben formar parte de la release:

```bash
git add pyproject.toml CHANGELOG.md ROADMAP.md README.md docs/release-process.md
git commit -m "Prepare release vX.Y.Z"
```

Antes de seguir, verifica el commit:

```bash
git show --stat --oneline HEAD
```

## Crear la tag anotada

Crea una tag anotada sobre el commit de release:

```bash
git tag -a vX.Y.Z -m "Release vX.Y.Z"
```

Comprueba que la tag apunta al commit correcto:

```bash
git show vX.Y.Z --stat
```

Buenas prácticas:

- no uses tags ligeras para releases;
- no reutilices una versión ya publicada;
- no muevas una tag pública a otro commit salvo que sea estrictamente imprescindible y todo el equipo lo tenga claro.

## Subir el commit y la tag a GitHub

Primero sube la rama:

```bash
git push origin main
```

Después sube la tag:

```bash
git push origin vX.Y.Z
```

Si en el futuro hay CI sobre tags, espera a que el estado quede en verde antes de publicar el release final.

## Publicar el release en GitHub desde la web

Ruta habitual:

1. Entra en el repositorio en GitHub.
2. Abre `Releases`.
3. Pulsa `Draft a new release`.
4. Selecciona la tag existente `vX.Y.Z`.
5. Usa como título `vX.Y.Z`.
6. Redacta las notas del release a partir de `CHANGELOG.md`.
7. Marca `Set as the latest release` solo si es una versión estable.
8. Marca `This is a pre-release` si es una `rc`, `beta` o similar.
9. Revisa todo una última vez y publica.

## Cómo redactar las notas del release

Las notas deben ser breves y útiles. Lo normal es incluir:

- resumen corto de la versión;
- cambios importantes para quien usa la aplicación;
- cambios operativos relevantes;
- posibles advertencias o pasos manuales tras actualizar.

Estructura recomendada:

```md
## Resumen
- ...

## Cambios principales
- ...

## Impacto operativo
- ...

## Notas
- ...
```

No copies ruido técnico innecesario si no aporta valor al usuario final.

## Alternativa con GitHub CLI

Si prefieres publicar el release por terminal y tienes `gh` configurado:

```bash
gh release create vX.Y.Z \
  --title "vX.Y.Z" \
  --notes-file release-notes.md
```

Para una pre-release:

```bash
gh release create vX.Y.Z-rc.1 \
  --title "vX.Y.Z-rc.1" \
  --notes-file release-notes.md \
  --prerelease
```

## Qué no hacer

- No crear la tag antes de pasar `make lint` y `make test`.
- No publicar una versión si `CHANGELOG.md` no refleja el contenido real.
- No editar una release para fingir una versión distinta de la tag.
- No sobrescribir una tag pública para “corregirla rápido”.
- No mezclar en el commit de release cambios ajenos a la versión.

## Si te equivocas

Si la tag se ha creado localmente pero aún no se ha publicado:

```bash
git tag -d vX.Y.Z
```

Si la tag ya se ha subido a GitHub pero todavía no debe existir, elimina primero la remota y luego la local:

```bash
git push origin :refs/tags/vX.Y.Z
git tag -d vX.Y.Z
```

Si la release ya se ha publicado y alguien puede haberla usado, lo más prudente suele ser:

- dejar esa tag como está;
- corregir el problema en una nueva versión;
- publicar `vX.Y.(Z+1)`.

## Lista de comprobación rápida

- [ ] `git status` limpio
- [ ] `main` actualizado con `git pull --ff-only`
- [ ] versión actualizada en `pyproject.toml`
- [ ] `CHANGELOG.md` revisado
- [ ] `ROADMAP.md` revisado si procede
- [ ] `make lint` en verde
- [ ] `make test` en verde
- [ ] commit `Prepare release vX.Y.Z`
- [ ] tag anotada `vX.Y.Z`
- [ ] `git show vX.Y.Z --stat` revisado
- [ ] `git push origin main`
- [ ] `git push origin vX.Y.Z`
- [ ] release publicado en GitHub con notas claras

## Comandos de referencia

```bash
git switch main
git pull --ff-only origin main
make lint
make test
git add pyproject.toml CHANGELOG.md ROADMAP.md README.md docs/release-process.md
git commit -m "Prepare release vX.Y.Z"
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git show vX.Y.Z --stat
git push origin main
git push origin vX.Y.Z
```
