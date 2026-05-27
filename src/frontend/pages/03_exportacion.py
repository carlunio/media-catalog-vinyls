from typing import Any

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

SELECTION_COLUMN = "Seleccionar"
REFERENCE_COLUMN = "REFERENCIA"


def _sync_export_selection(preview_ids: list[str]) -> list[str]:
    preview_signature = tuple(preview_ids)
    current_signature = st.session_state.get("vinilos_export_preview_signature")
    if current_signature != preview_signature:
        st.session_state["vinilos_export_preview_signature"] = preview_signature
        st.session_state["vinilos_export_selected_ids"] = list(preview_ids)
        st.session_state.pop("vinilos_export_selection_editor", None)

    selected_ids = [
        item_id
        for item_id in list(st.session_state.get("vinilos_export_selected_ids") or [])
        if item_id in preview_ids
    ]
    st.session_state["vinilos_export_selected_ids"] = selected_ids
    return selected_ids


def _selection_rows(preview_rows: list[dict[str, Any]], selected_ids: list[str]) -> list[dict[str, Any]]:
    selected_ids_set = set(selected_ids)
    rows: list[dict[str, Any]] = []
    for row in preview_rows:
        item_id = str(row.get(REFERENCE_COLUMN) or "").strip()
        rows.append({SELECTION_COLUMN: item_id in selected_ids_set, **row})
    return rows


def _rows_from_editor_value(value: Any) -> list[dict[str, Any]]:
    if hasattr(value, "to_dict"):
        return list(value.to_dict(orient="records"))
    if isinstance(value, list):
        return [dict(row) for row in value]
    return []


@st.dialog("Exportación completada", width="medium", dismissible=False)
def _export_result_dialog() -> None:
    export_bytes = st.session_state.get("vinilos_export_bytes")
    export_name = str(st.session_state.get("vinilos_export_filename") or "vinilos.csv")
    export_path = str(st.session_state.get("vinilos_export_path") or "")
    export_rows = int(st.session_state.get("vinilos_export_rows") or 0)
    export_ids = list(st.session_state.get("vinilos_export_ids") or [])

    st.success(f"Se ha generado `{export_name}` con {export_rows} filas seleccionadas.")
    if export_path:
        st.caption(f"El fichero ya se ha guardado en la máquina donde corre la app: `{export_path}`.")

    if isinstance(export_bytes, (bytes, bytearray)):
        st.download_button(
            label="Guardar también en este PC",
            data=bytes(export_bytes),
            file_name=export_name,
            mime="text/csv",
            type="primary",
            width="stretch",
        )

    st.markdown(
        "Si quieres, ahora puedes dejar sin operación las fichas seleccionadas y exportadas."
    )
    secondary_col, primary_col = st.columns(2, gap="small")

    with secondary_col:
        if st.button("Cerrar sin cambiar estados", width="stretch"):
            st.session_state["vinilos_export_dialog_open"] = False
            st.rerun()

    with primary_col:
        if st.button("Quitar operación a exportados", width="stretch"):
            try:
                result = api_post(
                    "/export/vinilos/clear-operation",
                    json={"ids": export_ids},
                    timeout=LONG_TIMEOUT_SECONDS,
                )
            except Exception as exc:
                st.error(f"No se pudieron limpiar las operaciones: {exc}")
            else:
                updated = int(result.get("updated") or 0)
                st.session_state["vinilos_export_dialog_open"] = False
                st.session_state["vinilos_export_flash"] = (
                    f"Se ha quitado la operación a {updated} fichas exportadas."
                )
                st.rerun()


st.markdown("""
Exporta la vista **export** a un fichero **CSV Importamatic (UTF-8, separado por `#`)**.
Solo se incluyen fichas con **Estado de carga** en **ALTA**, **CAMBIO** o **BAJA**.
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
selected_ids = _sync_export_selection(preview_ids)

summary_left, summary_right = st.columns([1, 2], gap="large")
with summary_left:
    st.metric("Fichas listas para exportar", preview_count)
with summary_right:
    st.caption(
        "La vista previa se carga automáticamente desde la vista `export` de DuckDB. "
        "Si cambian los estados en la base de datos, esta tabla se actualiza al recargar la página."
    )

if preview_rows:
    controls_container = st.container()
    selection_rows = _selection_rows(preview_rows, selected_ids)
    edited_rows = st.data_editor(
        selection_rows,
        hide_index=True,
        use_container_width=True,
        disabled=preview_columns,
        column_config={
            SELECTION_COLUMN: st.column_config.CheckboxColumn(
                "Exportar",
                help="Marca las fichas sobre las que quieres actuar en la exportación y en la limpieza posterior de operación.",
                default=True,
                width="small",
            )
        },
        key="vinilos_export_selection_editor",
    )
    edited_selection_rows = _rows_from_editor_value(edited_rows)
    selected_ids = [
        str(row.get(REFERENCE_COLUMN) or "").strip()
        for row in edited_selection_rows
        if bool(row.get(SELECTION_COLUMN)) and str(row.get(REFERENCE_COLUMN) or "").strip()
    ]
    st.session_state["vinilos_export_selected_ids"] = selected_ids
    all_selected = len(selected_ids) == len(preview_ids)
    select_all_key = f"vinilos_export_select_all_{preview_count}_{int(all_selected)}"
    export_disabled = len(selected_ids) == 0

    with controls_container:
        selection_toggle_col, selection_status_col, export_button_col = st.columns([1.2, 1.6, 0.8], gap="large")
        with selection_toggle_col:
            select_all_value = st.checkbox(
                "Seleccionar todas las filas exportables",
                value=all_selected,
                key=select_all_key,
            )
        with selection_status_col:
            st.caption(f"Seleccionadas para exportar: {len(selected_ids)} de {preview_count}.")
        with export_button_col:
            export_requested = st.button("Exportar a CSV", type="primary", disabled=export_disabled, width="stretch")

        if select_all_value != all_selected:
            st.session_state["vinilos_export_selected_ids"] = list(preview_ids) if select_all_value else []
            st.session_state.pop("vinilos_export_selection_editor", None)
            st.rerun()
else:
    st.info("No hay fichas con estado de carga `ALTA`, `CAMBIO` o `BAJA`.")
    selected_ids = []
    st.session_state["vinilos_export_selected_ids"] = []
    export_requested = False

if export_requested:
    with st.spinner("Generando archivo…"):
        try:
            result = api_post(
                "/export/vinilos/csv",
                json={"ids": selected_ids},
                timeout=LONG_TIMEOUT_SECONDS,
            )
            filename = str(result.get("filename") or "vinilos.csv")
            file_bytes = api_get_bytes(
                "/export/vinilos/file",
                params={"filename": filename},
                timeout=LONG_TIMEOUT_SECONDS,
            )
            st.session_state["vinilos_export_bytes"] = file_bytes
            st.session_state["vinilos_export_filename"] = filename
            st.session_state["vinilos_export_path"] = str(result.get("path") or "")
            st.session_state["vinilos_export_rows"] = int(result.get("rows") or 0)
            st.session_state["vinilos_export_ids"] = list(result.get("ids") or selected_ids)
            st.session_state["vinilos_export_dialog_open"] = True
            st.rerun()
        except Exception as exc:
            st.error(f"No se pudo exportar el catálogo: {exc}")

download_bytes = st.session_state.get("vinilos_export_bytes")
download_name = st.session_state.get("vinilos_export_filename", "vinilos.csv")
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
        mime="text/csv",
        width="stretch",
    )

if st.session_state.get("vinilos_export_dialog_open"):
    _export_result_dialog()
