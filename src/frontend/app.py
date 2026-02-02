import streamlit as st

st.set_page_config(
    page_title="Catálogo de vinilos",
    layout="wide"
)

st.title("📀 Catálogo de vinilos")

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