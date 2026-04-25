import streamlit as st

try:
    from src.frontend.utils import (
        LONG_TIMEOUT_SECONDS,
        api_get,
        api_get_bytes,
        configure_page,
        render_icon_heading,
        show_backend_status,
    )
except ModuleNotFoundError:  # pragma: no cover
    from frontend.utils import (
        LONG_TIMEOUT_SECONDS,
        api_get,
        api_get_bytes,
        configure_page,
        render_icon_heading,
        show_backend_status,
    )

configure_page("Exportación | Catálogo de vinilos")

render_icon_heading("Exportación", icon="file-export", level=1)
show_backend_status()

st.markdown("""
Exporta la tabla **vinilos** a un fichero **TXT tabulado (UTF-8)**.
""")

if st.button("Exportar a TXT"):
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
            st.success(
                f"Exportación completada: {result.get('path')} "
                f"({int(result.get('rows') or 0)} filas)"
            )
        except Exception as exc:
            st.error(f"No se pudo exportar el catálogo: {exc}")

download_bytes = st.session_state.get("vinilos_export_bytes")
download_name = st.session_state.get("vinilos_export_filename", "vinilos.txt")
if isinstance(download_bytes, (bytes, bytearray)):
    st.download_button(
        label="Descargar vinilos.txt",
        data=bytes(download_bytes),
        file_name=str(download_name),
        mime="text/plain",
    )
