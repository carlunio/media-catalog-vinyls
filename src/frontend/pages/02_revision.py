import streamlit as st
import requests
from datetime import datetime

API_URL = "http://127.0.0.1:8000"

# =========================
# NORMALIZADORES
# =========================
def normalizar_año(valor):
    if valor is None:
        return None
    if isinstance(valor, int):
        return valor
    if isinstance(valor, str):
        valor = valor.strip()
        if len(valor) >= 4 and valor[:4].isdigit():
            return int(valor[:4])
    return None


# =========================
# UI
# =========================
st.title("📝 Revisión y edición de vinilos")

# ---------- FASE A ----------
st.subheader("1️⃣ Preparación automática")

if st.button("Preparar fichas desde vinilos_raw"):
    resp = requests.post(f"{API_URL}/vinilos/preparar")
    resp.raise_for_status()
    n = resp.json()["creados"]
    st.success(f"Se han creado {n} fichas nuevas en vinilos")

st.divider()

# ---------- FASE B ----------
st.subheader("2️⃣ Revisión manual")

resp = requests.get(f"{API_URL}/vinilos")
resp.raise_for_status()
rows = resp.json()

if not rows:
    st.info("No hay vinilos para revisar")
    st.stop()

id_list = [r["id"] for r in rows]
total = len(id_list)

if "vinilo_idx" not in st.session_state:
    st.session_state["vinilo_idx"] = 0

selected_id = st.selectbox(
    "Selecciona un vinilo",
    id_list,
    index=st.session_state["vinilo_idx"]
)

st.session_state["vinilo_idx"] = id_list.index(selected_id)
st.caption(f"Registro {st.session_state['vinilo_idx'] + 1} de {total}")

# ---------- NAVEGACIÓN ----------
nav_l, nav_r = st.columns(2)

with nav_l:
    if st.button("⬅️ Anterior", disabled=st.session_state["vinilo_idx"] == 0):
        st.session_state["vinilo_idx"] -= 1
        st.rerun()

with nav_r:
    if st.button("Siguiente ➡️", disabled=st.session_state["vinilo_idx"] == total - 1):
        st.session_state["vinilo_idx"] += 1
        st.rerun()

# ---------- CARGA DE DATOS ----------
resp = requests.get(f"{API_URL}/vinilos/{selected_id}")
resp.raise_for_status()
data = resp.json()

# ---------- FORMULARIO ----------
with st.form("form_revision"):
    st.markdown(f"### Vinilo: `{selected_id}`")

    # ---------- FILA 1 ----------
    c1, c2, c3 = st.columns(3)
    with c1:
        tipo_articulo = st.text_input("Tipo de artículo", data["tipo_articulo"])
    with c2:
        estado_carga = st.selectbox(
            "Estado de carga",
            ["Para subir", "Para actualizar", "Subido"],
            index=["Para subir", "Para actualizar", "Subido"].index(data["estado_carga"])
        )
    with c3:
        estado_stock = st.selectbox(
            "Estado de stock",
            ["En stock", "Vendido", "Extraviado"],
            index=["En stock", "Vendido", "Extraviado"].index(data["estado_stock"])
        )

    # ---------- FILA 2 ----------
    c4, c5, c6 = st.columns([2, 1, 1])
    with c4:
        nombre = st.text_input("Nombre", data["nombre"] or "")
    with c5:
        año = st.number_input(
            "Año",
            value=normalizar_año(data["año"]) or 0,
            step=1,
            min_value=0
        )
    with c6:
        pais = st.text_input("País", data["pais"] or "")

    # ---------- FILA 3 ----------
    c7, c8, c9 = st.columns([2, 1, 1])
    with c7:
        artista = st.text_input("Artista", data["artista"] or "")
    with c8:
        generos = st.text_input("Géneros", data["generos"] or "")
    with c9:
        estilos = st.text_input("Estilos", data["estilos"] or "")

    # ---------- FILA 4 ----------
    c10, c11, c12 = st.columns([3, 1, 1])
    with c10:
        sello = st.text_input("Sello", data["sello"] or "")
    with c11:
        duracion_total = st.text_input("Duración", data["duracion_total"] or "")
    with c12:
        estimated_weight = st.number_input(
            "Peso (g)",
            value=int(data["estimated_weight"] or 0),
            step=10,
            min_value=0
        )

    # ---------- FILA 5 ----------
    c13, c14 = st.columns(2)
    with c13:
        tracklist = st.text_area("Tracklist", data["tracklist"] or "", height=200)
    with c14:
        notas = st.text_area("Notas", data["notas"] or "", height=200)

    # ---------- FILA 6 ----------
    c15, c16, c17 = st.columns([1, 1, 2])

    with c15:
        estado_conservacion = st.selectbox(
            "Estado conservación",
            ["", "Aceptable", "Bueno", "Muy bueno", "Excelente", "Como nuevo"],
            index=0 if not data["estado_conservacion"] else
            ["", "Aceptable", "Bueno", "Muy bueno", "Excelente", "Como nuevo"]
            .index(data["estado_conservacion"])
        )

    with c16:
        info = (
            f" (mín. Discogs: {data['menor_precio']:.2f} $)"
            if data["menor_precio"] is not None else
            " (sin datos Discogs)"
        )
        precio = st.number_input(
            f"Precio (€){info}",
            value=float(data["precio"] or 0.0),
            step=1.0,
            min_value=0.0
        )

    with c17:
        st.markdown(" ")
        guardar = st.form_submit_button("💾 Guardar cambios")

    if guardar:
        payload = {
            "tipo_articulo": tipo_articulo,
            "nombre": nombre,
            "artista": artista,
            "año": normalizar_año(año),
            "sello": sello,
            "pais": pais,
            "duracion_total": duracion_total,
            "estimated_weight": estimated_weight,
            "generos": generos,
            "estilos": estilos,
            "tracklist": tracklist,
            "estado_conservacion": estado_conservacion,
            "precio": precio,
            "estado_carga": estado_carga,
            "estado_stock": estado_stock,
            "notas": notas,
            "updated_at": datetime.now().isoformat()
        }

        requests.put(
            f"{API_URL}/vinilos/{selected_id}",
            json=payload
        )

        st.success("Ficha actualizada correctamente")
