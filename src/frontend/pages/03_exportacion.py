import streamlit as st

try:
    from src.frontend.utils import (
        LONG_TIMEOUT_SECONDS,
        api_get,
        api_get_bytes,
        api_post,
        configure_page,
        render_icon_heading,
    )
except ModuleNotFoundError:  # pragma: no cover
    from frontend.utils import (
        LONG_TIMEOUT_SECONDS,
        api_get,
        api_get_bytes,
        api_post,
        configure_page,
        render_icon_heading,
    )

configure_page("Exportación | Catálogo de vinilos")

render_icon_heading("Exportación", icon="file-export", level=1)


@st.dialog("Exportación completada", width="medium", dismissible=False)
def _export_result_dialog() -> None:
    export_bytes = st.session_state.get("vinilos_export_bytes")
    export_name = str(st.session_state.get("vinilos_export_filename") or "vinilos.txt")
    export_path = str(st.session_state.get("vinilos_export_path") or "")
    export_rows = int(st.session_state.get("vinilos_export_rows") or 0)
    export_ids = list(st.session_state.get("vinilos_export_ids") or [])

    st.success(f"Se ha generado `{export_name}` con {export_rows} filas.")
    if export_path:
        st.caption(f"El fichero ya se ha guardado en la máquina donde corre la app: `{export_path}`.")

    if isinstance(export_bytes, (bytes, bytearray)):
        st.download_button(
            label="Guardar también en este PC",
            data=bytes(export_bytes),
            file_name=export_name,
            mime="text/plain",
            type="primary",
            width="stretch",
        )

    st.markdown(
        "Si quieres, ahora puedes marcar en la base de datos todos los registros exportados como **Subido**."
    )
    secondary_col, primary_col = st.columns(2, gap="small")

    with secondary_col:
        if st.button("Cerrar sin cambiar estados", width="stretch"):
            st.session_state["vinilos_export_dialog_open"] = False
            st.rerun()

    with primary_col:
        if st.button('Marcar exportados como "Subido"', width="stretch"):
            try:
                result = api_post(
                    "/export/vinilos/mark-uploaded",
                    json={"ids": export_ids},
                    timeout=LONG_TIMEOUT_SECONDS,
                )
            except Exception as exc:
                st.error(f"No se pudieron actualizar los estados de carga: {exc}")
            else:
                updated = int(result.get("updated") or 0)
                st.session_state["vinilos_export_dialog_open"] = False
                st.session_state["vinilos_export_flash"] = (
                    f'Se han marcado {updated} fichas exportadas como "Subido".'
                )
                st.rerun()


st.markdown("""
Exporta la vista **export** a un fichero **TXT tabulado (UTF-8)**.
Solo se incluyen fichas con **Estado de carga** en **Para subir** o **Para actualizar**.
""")

flash_message = str(st.session_state.pop("vinilos_export_flash", "") or "").strip()
if flash_message:
    st.success(flash_message)

try:
    preview = api_get("/export/vinilos/preview", timeout=LONG_TIMEOUT_SECONDS)
except Exception as exc:
    st.error(f"No se pudo cargar la vista previa de exportación: {exc}")
    st.stop()

preview_columns = list(preview.get("columns") or [])
preview_rows = list(preview.get("rows") or [])
preview_ids = list(preview.get("ids") or [])
preview_count = int(preview.get("rows_count") or len(preview_rows))

summary_left, summary_right = st.columns([1, 2], gap="large")
with summary_left:
    st.metric("Fichas listas para exportar", preview_count)
with summary_right:
    st.caption(
        "La vista previa se carga automáticamente desde la vista `export` de DuckDB. "
        "Si cambian los estados en la base de datos, esta tabla se actualiza al recargar la página."
    )

if preview_rows:
    st.dataframe(preview_rows, use_container_width=True, hide_index=True)
else:
    st.info("No hay fichas con estado de carga `Para subir` o `Para actualizar`.")

export_disabled = preview_count == 0
if st.button("Exportar a TXT", type="primary", disabled=export_disabled):
    with st.spinner("Generando archivo…"):
        try:
            result = api_get("/export/vinilos/txt", timeout=LONG_TIMEOUT_SECONDS)
            filename = str(result.get("filename") or "vinilos.txt")
            file_bytes = api_get_bytes(
                "/export/vinilos/file",
                params={"filename": filename},
                timeout=LONG_TIMEOUT_SECONDS,
            )
            st.session_state["vinilos_export_bytes"] = file_bytes
            st.session_state["vinilos_export_filename"] = filename
            st.session_state["vinilos_export_path"] = str(result.get("path") or "")
            st.session_state["vinilos_export_rows"] = int(result.get("rows") or 0)
            st.session_state["vinilos_export_ids"] = list(result.get("ids") or preview_ids)
            st.session_state["vinilos_export_dialog_open"] = True
            st.rerun()
        except Exception as exc:
            st.error(f"No se pudo exportar el catálogo: {exc}")

download_bytes = st.session_state.get("vinilos_export_bytes")
download_name = st.session_state.get("vinilos_export_filename", "vinilos.txt")
download_path = str(st.session_state.get("vinilos_export_path") or "")
download_rows = int(st.session_state.get("vinilos_export_rows") or 0)
if isinstance(download_bytes, (bytes, bytearray)):
    st.divider()
    render_icon_heading("Última exportación generada", icon="download", level=2)
    if download_path:
        st.caption(
            f"Guardada en `{download_path}` con {download_rows} filas. "
            "También puedes descargar una copia local desde aquí."
        )
    st.download_button(
        label="Guardar una copia en este PC",
        data=bytes(download_bytes),
        file_name=str(download_name),
        mime="text/plain",
        width="stretch",
    )

if st.session_state.get("vinilos_export_dialog_open"):
    _export_result_dialog()
