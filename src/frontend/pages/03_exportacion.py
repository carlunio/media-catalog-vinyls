from pathlib import Path

import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000"

st.title("📤 Exportación")

st.markdown("""
Exporta la tabla **vinilos** a un fichero **TXT tabulado (UTF-8)**.
""")

if st.button("📄 Exportar a TXT"):
    with st.spinner("Generando archivo…"):
        resp = requests.get(f"{API_URL}/export/vinilos/txt")
        resp.raise_for_status()

    path = resp.json()["path"]
    file_path = Path(path)

    if file_path.exists():
        st.success("Exportación completada")

        st.download_button(
            label="⬇️ Descargar vinilos.txt",
            data=file_path.read_text(encoding="utf-8"),
            file_name="vinilos.txt",
            mime="text/plain",
        )
