import streamlit as st
import requests

try:
    from src.frontend.utils import (
        LONG_TIMEOUT_SECONDS,
        api_get,
        api_post,
        configure_page,
        render_empty_icon,
        render_icon_heading,
        render_nested_data_tree,
    )
except ModuleNotFoundError:  # pragma: no cover
    from frontend.utils import (
        LONG_TIMEOUT_SECONDS,
        api_get,
        api_post,
        configure_page,
        render_empty_icon,
        render_icon_heading,
        render_nested_data_tree,
    )

configure_page("Discogs | Catálogo de vinilos")

render_icon_heading("Ficha de Discogs", icon="magnifying-glass", level=1)


def _show_discogs_http_error(exc, *, fallback_prefix):
    response = exc.response
    if response is None:
        st.error(f"{fallback_prefix}: {exc}")
        return

    detail = None
    try:
        payload = response.json()
        if isinstance(payload, dict):
            detail = payload.get("detail")
    except ValueError:
        detail = None

    if isinstance(detail, dict):
        title = str(detail.get("title") or "Error en Discogs").strip()
        message = str(detail.get("message") or fallback_prefix).strip()
        hint = str(detail.get("hint") or "").strip()
        upstream_message = str(detail.get("upstream_message") or "").strip()

        st.error(f"{title}: {message}")
        if hint:
            st.caption(hint)
        if upstream_message and upstream_message != message:
            st.caption(f"Detalle técnico: {upstream_message}")
        return

    if isinstance(detail, str) and detail.strip():
        st.error(detail.strip())
        return

    st.error(f"{fallback_prefix}: HTTP {response.status_code}")

query = st.text_input(
    "Buscar en Discogs",
    placeholder="Código, catálogo, barcode, artista + disco…"
)

# -------------------------
# BÚSQUEDA
# -------------------------
if query:
    with st.spinner("Buscando en Discogs…"):
        try:
            results = api_get(
                "/discogs/search",
                params={"q": query},
                timeout=LONG_TIMEOUT_SECONDS,
            )
        except requests.HTTPError as exc:
            _show_discogs_http_error(exc, fallback_prefix="No se pudo completar la búsqueda en Discogs")
            st.stop()
        except requests.RequestException as exc:
            st.error(f"No se pudo conectar con el backend: {exc}")
            st.stop()

    if not results:
        st.warning("No se encontraron resultados.")
        st.stop()

    render_icon_heading("Resultados", icon="list", level=2)

    for r in results:
        st.markdown("---")
        c1, c2 = st.columns([1, 4])

        with c1:
            if r.get("thumb"):
                st.image(r["thumb"], width=120)
            else:
                render_empty_icon("record-vinyl", "Sin imagen")

        with c2:
            st.markdown(f"**{r['title']}**")
            st.caption(f"Discogs ID: {r['id']}")

            if st.button("Seleccionar este release", key=f"sel_{r['id']}"):
                st.session_state["selected_release_id"] = r["id"]
                st.session_state["discogs_release_tree_expand_all"] = False
                st.session_state.pop("confirm_overwrite", None)

# -------------------------
# SELECCIÓN
# -------------------------
if "selected_release_id" in st.session_state:
    st.divider()
    release_id = st.session_state["selected_release_id"]

    try:
        release_data = api_get(
            f"/discogs/release/{release_id}",
            timeout=LONG_TIMEOUT_SECONDS,
        )
    except requests.HTTPError as exc:
        _show_discogs_http_error(exc, fallback_prefix="No se pudo cargar el release desde Discogs")
        st.stop()
    except requests.RequestException as exc:
        st.error(f"No se pudo cargar el release: {exc}")
        st.stop()

    render_icon_heading(str(release_data.get("title") or "Release"), icon="record-vinyl", level=3)
    st.caption(f"Discogs source ID: {release_id}")

    render_nested_data_tree(release_data, state_key="discogs_release_tree")

    # -------------------------
    # GUARDADO
    # -------------------------
    render_icon_heading("Guardar en vinilos_raw", icon="database", level=3)

    with st.form("guardar_form"):
        catalog_id = st.text_input("ID para tu catálogo")
        submitted = st.form_submit_button("Guardar")

    if submitted:
        if not catalog_id:
            st.error("Debes introducir un ID")
        else:
            try:
                exists = api_get(f"/vinilos_raw/exists/{catalog_id}")["exists"]
                if exists:
                    info = api_get(f"/vinilos_raw/info/{catalog_id}")["info"]
                    st.session_state["confirm_overwrite"] = {
                        "id": catalog_id,
                        "info": info,
                    }
                else:
                    api_post(
                        "/vinilos_raw",
                        json={
                            "id": catalog_id,
                            "data": release_data,
                            "overwrite": False,
                        },
                        timeout=LONG_TIMEOUT_SECONDS,
                    )
                    st.success("Vinilo guardado correctamente")
            except requests.RequestException as exc:
                st.error(f"No se pudo guardar el vinilo: {exc}")

    # -------------------------
    # CONFIRMACIÓN OVERWRITE
    # -------------------------
    if "confirm_overwrite" in st.session_state:
        data = st.session_state["confirm_overwrite"]

        st.warning(
            f"El ID **{data['id']}** ya existe\n\n"
            f"**{data['info']}**\n\n"
            "¿Seguro que quieres sobrescribirlo?"
        )

        c1, c2 = st.columns([2, 1])

        with c1:
            if st.button("Cancelar"):
                st.session_state.pop("confirm_overwrite")

        with c2:
            if st.button("Sobrescribir"):
                try:
                    api_post(
                        "/vinilos_raw",
                        json={
                            "id": data["id"],
                            "data": release_data,
                            "overwrite": True,
                        },
                        timeout=LONG_TIMEOUT_SECONDS,
                    )
                    st.success("Vinilo sobrescrito")
                    st.session_state.pop("confirm_overwrite")
                except requests.RequestException as exc:
                    st.error(f"No se pudo sobrescribir el vinilo: {exc}")
