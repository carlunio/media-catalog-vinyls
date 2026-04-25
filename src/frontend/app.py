from pathlib import Path

import streamlit as st

try:
    from src.frontend.utils import (
        configure_page,
        get_app_version_label,
        get_changelog_path,
        show_backend_status,
    )
except ModuleNotFoundError:  # pragma: no cover
    from frontend.utils import (
        configure_page,
        get_app_version_label,
        get_changelog_path,
        show_backend_status,
    )

configure_page()

st.title("📀 Catálogo de vinilos")
st.caption(f"Versión actual: {get_app_version_label()}")
show_backend_status()

st.markdown(
    """
    Bienvenido al catálogo.

    Usa el menú lateral para:
    - 📥 **API Discogs**: buscar fichas en Discogs, elegir una y guardarla cruda en la base de datos.
    - 📝 **Revisión**: procesar todas las fichas crudas y revisar el formulario para modificar y completar la información, que se guarda en la base de datos.
    - 📤 **Exportación**...
    """
)

st.info("Selecciona una opción en el menú de la izquierda.")

changelog_path = get_changelog_path()
if changelog_path:
    st.caption(f"Historial de cambios: {Path(changelog_path).name}")
