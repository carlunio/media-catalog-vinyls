import streamlit as st

try:
    from src.frontend.utils import (
        configure_page,
        render_icon_cards,
        render_icon_heading,
    )
except ModuleNotFoundError:  # pragma: no cover
    from frontend.utils import (
        configure_page,
        render_icon_cards,
        render_icon_heading,
    )

configure_page()

render_icon_heading("Catálogo de vinilos", icon="record-vinyl", level=1)

st.write("Bienvenido al catálogo.")

render_icon_cards(
    [
        (
            "magnifying-glass",
            "Discogs",
            "Busca releases, revisa la ficha original y guarda las fichas de Discogs en la base de datos.",
        ),
        (
            "pen-to-square",
            "Revisión",
            "Prepara fichas desde las fichas de Discogs y completa la información final para el catálogo.",
        ),
        (
            "file-export",
            "Exportación",
            "Genera el TXT tabulado final para usarlo fuera de la aplicación.",
        ),
    ]
)

st.info("Selecciona una opción en el menú de la izquierda.")
