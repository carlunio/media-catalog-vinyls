from pathlib import Path

import streamlit as st

try:
    from src.frontend.utils import (
        configure_page,
        get_app_version_label,
        get_changelog_path,
        render_icon_cards,
        render_icon_heading,
        show_backend_status,
    )
except ModuleNotFoundError:  # pragma: no cover
    from frontend.utils import (
        configure_page,
        get_app_version_label,
        get_changelog_path,
        render_icon_cards,
        render_icon_heading,
        show_backend_status,
    )

configure_page()

render_icon_heading("Catálogo de vinilos", icon="record-vinyl", level=1)
st.caption(f"Versión actual: {get_app_version_label()}")
show_backend_status()

st.write("Bienvenido al catálogo.")

render_icon_cards(
    [
        (
            "magnifying-glass",
            "Discogs",
            "Busca releases, revisa la ficha original y guarda el material crudo en la base de datos.",
        ),
        (
            "pen-to-square",
            "Revisión",
            "Prepara fichas desde vinilos_raw y completa la información final para el catálogo.",
        ),
        (
            "file-export",
            "Exportación",
            "Genera el TXT tabulado final para usarlo fuera de la aplicación.",
        ),
    ]
)

st.info("Selecciona una opción en el menú de la izquierda.")

changelog_path = get_changelog_path()
if changelog_path:
    st.caption(f"Historial de cambios: {Path(changelog_path).name}")
