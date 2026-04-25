import streamlit as st

try:
    from src.backend.normalizers import normalizar_año
except ModuleNotFoundError:  # pragma: no cover
    from backend.normalizers import normalizar_año

try:
    from src.frontend.utils import (
        api_get,
        api_post,
        api_put,
        configure_page,
        render_icon_heading,
        show_backend_status,
    )
except ModuleNotFoundError:  # pragma: no cover
    from frontend.utils import (
        api_get,
        api_post,
        api_put,
        configure_page,
        render_icon_heading,
        show_backend_status,
    )

configure_page("Revisión | Catálogo de vinilos")


def _safe_index(options, value, default=0):
    try:
        return options.index(value)
    except ValueError:
        return default


render_icon_heading("Revisión y edición de vinilos", icon="pen-to-square", level=1)
show_backend_status()

render_icon_heading("Preparación automática", icon="gears", level=2)

if st.button("Preparar fichas desde vinilos_raw"):
    try:
        result = api_post("/vinilos/preparar")
        n = result["creados"]
        st.success(f"Se han creado {n} fichas nuevas en vinilos")
    except Exception as exc:
        st.error(f"No se pudieron preparar las fichas: {exc}")

st.divider()

render_icon_heading("Revisión manual", icon="sliders", level=2)

try:
    rows = api_get("/vinilos")
except Exception as exc:
    st.error(f"No se pudo cargar el listado de vinilos: {exc}")
    st.stop()

if not rows:
    st.info("No hay vinilos para revisar")
    st.stop()

id_list = [r["id"] for r in rows]
total = len(id_list)

if "vinilo_idx" not in st.session_state:
    st.session_state["vinilo_idx"] = 0
else:
    st.session_state["vinilo_idx"] = max(0, min(st.session_state["vinilo_idx"], total - 1))

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
    if st.button("Anterior", disabled=st.session_state["vinilo_idx"] == 0):
        st.session_state["vinilo_idx"] -= 1
        st.rerun()

with nav_r:
    if st.button("Siguiente", disabled=st.session_state["vinilo_idx"] == total - 1):
        st.session_state["vinilo_idx"] += 1
        st.rerun()

try:
    data = api_get(f"/vinilos/{selected_id}")
except Exception as exc:
    st.error(f"No se pudo cargar la ficha {selected_id}: {exc}")
    st.stop()

with st.form("form_revision"):
    st.markdown(f"### Vinilo: `{selected_id}`")

    c1, c2, c3 = st.columns(3)
    with c1:
        tipo_articulo = st.text_input("Tipo de artículo", data["tipo_articulo"])
    with c2:
        estado_carga_options = ["Para subir", "Para actualizar", "Subido"]
        estado_carga = st.selectbox(
            "Estado de carga",
            estado_carga_options,
            index=_safe_index(estado_carga_options, data["estado_carga"]),
        )
    with c3:
        estado_stock_options = ["En stock", "Vendido", "Extraviado"]
        estado_stock = st.selectbox(
            "Estado de stock",
            estado_stock_options,
            index=_safe_index(estado_stock_options, data["estado_stock"]),
        )

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

    c7, c8, c9 = st.columns([2, 1, 1])
    with c7:
        artista = st.text_input("Artista", data["artista"] or "")
    with c8:
        generos = st.text_input("Géneros", data["generos"] or "")
    with c9:
        estilos = st.text_input("Estilos", data["estilos"] or "")

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

    c13, c14 = st.columns(2)
    with c13:
        tracklist = st.text_area("Tracklist", data["tracklist"] or "", height=200)
    with c14:
        notas = st.text_area("Notas", data["notas"] or "", height=200)

    c15, c16, c17 = st.columns([1, 1, 2])

    with c15:
        estado_conservacion_options = [
            "",
            "Aceptable",
            "Bueno",
            "Muy bueno",
            "Excelente",
            "Como nuevo",
        ]
        estado_conservacion = st.selectbox(
            "Estado conservación",
            estado_conservacion_options,
            index=_safe_index(
                estado_conservacion_options,
                data["estado_conservacion"],
                default=0,
            ),
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
        guardar = st.form_submit_button("Guardar cambios")

    if guardar:
        payload = {
            "tipo_articulo": tipo_articulo,
            "nombre": nombre,
            "artista": artista,
            "año": normalizar_año(año) if año else None,
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
        }

        try:
            api_put(f"/vinilos/{selected_id}", json=payload)
            st.success("Ficha actualizada correctamente")
        except Exception as exc:
            st.error(f"No se pudo actualizar la ficha: {exc}")
