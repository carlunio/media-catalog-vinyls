import streamlit as st
import requests
import json

API_URL = "http://127.0.0.1:8000"

st.title("📥 Ficha de Discogs")

query = st.text_input(
    "Buscar en Discogs",
    placeholder="Código, catálogo, barcode, artista + disco…"
)

# -------------------------
# BÚSQUEDA
# -------------------------
if query:
    with st.spinner("Buscando en Discogs…"):
        resp = requests.get(
            f"{API_URL}/discogs/search",
            params={"q": query},
            timeout=10
        )

        if resp.status_code == 429:
            st.error("🚦 Demasiadas peticiones a Discogs. Espera unos segundos.")
            st.stop()

        resp.raise_for_status()
        results = resp.json()

    if not results:
        st.warning("No se encontraron resultados.")
        st.stop()

    st.subheader("Resultados")

    for r in results:
        st.markdown("---")
        c1, c2 = st.columns([1, 4])

        with c1:
            if r.get("thumb"):
                st.image(r["thumb"], width=120)
            else:
                st.write("📀")

        with c2:
            st.markdown(f"**{r['title']}**")
            st.caption(f"Discogs ID: {r['id']}")

            if st.button("Seleccionar este release", key=f"sel_{r['id']}"):
                st.session_state["selected_release_id"] = r["id"]
                st.session_state.pop("confirm_overwrite", None)

# -------------------------
# SELECCIÓN
# -------------------------
if "selected_release_id" in st.session_state:
    st.divider()
    release_id = st.session_state["selected_release_id"]

    resp = requests.get(
        f"{API_URL}/discogs/release/{release_id}",
        timeout=10
    )
    resp.raise_for_status()
    release_data = resp.json()

    st.markdown(f"### {release_data.get('title')}")
    st.caption(f"Discogs source ID: {release_id}")

    st.json(release_data)

    # -------------------------
    # GUARDADO
    # -------------------------
    st.markdown("### Guardar en vinilos_raw")

    with st.form("guardar_form"):
        catalog_id = st.text_input("ID para tu catálogo")
        submitted = st.form_submit_button("Guardar")

    if submitted:
        if not catalog_id:
            st.error("Debes introducir un ID")
        else:
            exists_resp = requests.get(
                f"{API_URL}/vinilos_raw/exists/{catalog_id}"
            )
            exists_resp.raise_for_status()
            exists = exists_resp.json()["exists"]

            if exists:
                info_resp = requests.get(
                    f"{API_URL}/vinilos_raw/info/{catalog_id}"
                )
                info_resp.raise_for_status()

                st.session_state["confirm_overwrite"] = {
                    "id": catalog_id,
                    "info": info_resp.json()["info"]
                }
            else:
                requests.post(
                    f"{API_URL}/vinilos_raw",
                    json={
                        "id": catalog_id,
                        "data": release_data,
                        "overwrite": False
                        }
                        )

                st.success("Vinilo guardado correctamente 🦆")

    # -------------------------
    # CONFIRMACIÓN OVERWRITE
    # -------------------------
    if "confirm_overwrite" in st.session_state:
        data = st.session_state["confirm_overwrite"]

        st.warning(
            f"⚠️ El ID **{data['id']}** ya existe\n\n"
            f"**{data['info']}**\n\n"
            "¿Seguro que quieres sobrescribirlo?"
        )

        c1, c2 = st.columns([2, 1])

        with c1:
            if st.button("Cancelar"):
                st.session_state.pop("confirm_overwrite")

        with c2:
            if st.button("Sobrescribir"):
                requests.post(
                    f"{API_URL}/vinilos_raw",
                    params={"id": data['id'], "overwrite": True},
                    json=release_data
                )
                st.success("Vinilo sobrescrito 🦆")
                st.session_state.pop("confirm_overwrite")
