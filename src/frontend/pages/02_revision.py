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
        render_empty_icon,
        render_icon_heading,
    )
except ModuleNotFoundError:  # pragma: no cover
    from frontend.utils import (
        api_get,
        api_post,
        api_put,
        configure_page,
        render_empty_icon,
        render_icon_heading,
    )

configure_page("Revisión | Catálogo de vinilos")


def _safe_index(options, value, default=0):
    try:
        return options.index(value)
    except ValueError:
        return default


def _field_options(allowed_values, field, current):
    base = [str(item).strip() for item in allowed_values.get(field, []) if str(item).strip()]
    options = [""]
    for item in base:
        if item not in options:
            options.append(item)
    current_value = str(current or "").strip()
    if current_value and current_value not in options:
        options.append(current_value)
    return options


def _field_key(record_id, field):
    return f"vinilo_revision_{record_id}_{field}"


def _display_text(value):
    text = str(value or "").strip()
    if text.lower() in {"none", "null", "nan"}:
        return ""
    return text


def _inject_revision_form_styles():
    st.markdown(
        """
        <style>
        .block-container,
        [data-testid="stAppViewBlockContainer"] {
            max-width: 100% !important;
            padding-left: 0.7rem;
            padding-right: 0.7rem;
            padding-top: 0.9rem;
        }
        .vinyl-form-panel {
            background: linear-gradient(180deg, rgba(255, 249, 242, 0.94) 0%, rgba(239, 231, 221, 0.96) 100%);
            border: 1px solid rgba(102, 88, 74, 0.18);
            border-radius: 14px;
            box-shadow: var(--mc-shadow, 0 16px 34px rgba(45, 39, 33, 0.08));
            margin-top: 0.45rem;
            padding: 1rem 1rem 0.95rem;
        }
        .vinyl-subpanel {
            background: transparent;
            border: none;
            border-radius: 0;
            height: 100%;
            padding: 0;
        }
        .vinyl-cover-panel .stImage img {
            border: 1px solid rgba(79, 109, 112, 0.28);
            border-radius: 12px;
            box-shadow: 0 12px 24px rgba(45, 39, 33, 0.1);
        }
        .vinyl-form-note {
            color: var(--mc-muted, #5f6d75);
            font-size: 0.88rem;
            line-height: 1.35;
            margin-top: 0.25rem;
        }
        .vinyl-form-label {
            border: 1px solid rgba(77, 70, 62, 0.22);
            border-radius: 10px;
            color: #22313a;
            font-size: 0.96rem;
            font-weight: 700;
            line-height: 1.1rem;
            margin-bottom: 0.34rem;
            padding: 0.45rem 0.58rem;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.22);
        }
        .vf-blue { background: #9babb8; }
        .vf-green { background: #afbb93; }
        .vf-yellow { background: #dcc283; }
        .vf-purple { background: #b59aad; }
        .vf-cyan { background: #93b4b2; }
        .vf-orange { background: #cf9a78; }
        .vf-steel { background: #95a6b2; }
        .vf-beige { background: #d9c5b2; }
        .vinyl-form-actions {
            background: transparent;
            border: none;
            border-radius: 0;
            margin-top: 0.75rem;
            padding: 0;
        }
        div[data-testid="stForm"] div[data-baseweb="select"] > div,
        div[data-testid="stForm"] input,
        div[data-testid="stForm"] textarea {
            background: rgba(255, 252, 248, 0.96);
            border-color: rgba(94, 84, 74, 0.28);
            border-radius: 12px;
        }
        div[data-testid="stForm"] input:disabled,
        div[data-testid="stForm"] textarea:disabled {
            background: rgba(241, 236, 229, 0.96) !important;
            color: #6a757d !important;
        }
        div[data-testid="stForm"] button[kind="primary"] {
            background: linear-gradient(180deg, var(--mc-accent, #bb6d47), var(--mc-accent-deep, #9e5637));
            border: 1px solid rgba(94, 54, 40, 0.28);
            box-shadow: 0 12px 24px rgba(158, 86, 55, 0.18);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_label(container, label, label_class):
    container.markdown(
        f"<div class='vinyl-form-label {label_class}'>{label}</div>",
        unsafe_allow_html=True,
    )


def _render_inline_widget(container, *, label, label_class, ratio=(0.36, 0.64), render):
    left_col, right_col = container.columns([ratio[0], ratio[1]], gap="small")
    _render_label(left_col, label, label_class)
    return render(right_col)


def _render_stacked_widget(container, *, label, label_class, render):
    _render_label(container, label, label_class)
    return render(container)


def _open_panel(container, panel_class="vinyl-subpanel"):
    container.markdown(f"<div class='{panel_class}'>", unsafe_allow_html=True)


def _close_panel(container):
    container.markdown("</div>", unsafe_allow_html=True)


render_icon_heading("Revisión y edición de vinilos", icon="pen-to-square", level=1)
_inject_revision_form_styles()

render_icon_heading("Preparación automática", icon="gears", level=2)

if st.button("Preparar fichas desde las fichas de Discogs"):
    try:
        result = api_post("/vinilos/preparar")
        n = result["creados"]
        st.success(f"Se han creado {n} fichas nuevas en vinilos")
    except Exception as exc:
        st.error(f"No se pudieron preparar las fichas: {exc}")

st.divider()

render_icon_heading("Revisión manual", icon="sliders", level=2)

try:
    options_payload = api_get("/vinilos/options")
except Exception as exc:
    st.error(f"No se pudieron cargar las opciones cerradas del formulario: {exc}")
    st.stop()

allowed_values = options_payload.get("allowed_values") if isinstance(options_payload, dict) else {}
if not isinstance(allowed_values, dict):
    allowed_values = {}

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
selector_labels = {}
for row in rows:
    record_id = str(row.get("id") or "").strip()
    if not record_id:
        continue
    nombre = _display_text(row.get("nombre")) or "(sin nombre)"
    selector_labels[record_id] = f"{record_id} | {nombre}"

if "vinilo_idx" not in st.session_state:
    st.session_state["vinilo_idx"] = 0
else:
    st.session_state["vinilo_idx"] = max(0, min(st.session_state["vinilo_idx"], total - 1))

selected_id = st.selectbox(
    "Selecciona un vinilo",
    id_list,
    index=st.session_state["vinilo_idx"],
    format_func=lambda value: selector_labels.get(value, value),
)

st.session_state["vinilo_idx"] = id_list.index(selected_id)
st.caption(
    f"Registro {st.session_state['vinilo_idx'] + 1} de {total}"
    + (
        f" · {selector_labels.get(selected_id, selected_id)}"
        if selected_id in selector_labels
        else ""
    )
)

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
    tipo_articulo_options = _field_options(allowed_values, "tipo_articulo", data.get("tipo_articulo"))
    estado_carga_options = _field_options(allowed_values, "estado_carga", data.get("estado_carga"))
    estado_stock_options = _field_options(allowed_values, "estado_stock", data.get("estado_stock"))
    estado_disco_options = _field_options(
        allowed_values,
        "estado_disco",
        data.get("estado_disco"),
    )
    estado_funda_options = _field_options(
        allowed_values,
        "estado_funda",
        data.get("estado_funda"),
    )
    st.markdown("<div class='vinyl-form-panel'>", unsafe_allow_html=True)

    top_image, top_meta, top_main, top_extra = st.columns([1.02, 1.16, 1.34, 1.12], gap="large")

    with top_image:
        _open_panel(st, "vinyl-subpanel vinyl-cover-panel")
        _render_label(st, "Portada", "vf-steel")
        if data.get("discogs_image_url"):
            st.image(str(data["discogs_image_url"]), width="stretch")
            st.markdown("<div class='vinyl-form-note'>Imagen procedente de la ficha de Discogs.</div>", unsafe_allow_html=True)
        else:
            render_empty_icon("record-vinyl", "Sin portada")
        _close_panel(st)

    with top_meta:
        _open_panel(st)
        meta_left, meta_right = st.columns(2, gap="small")
        _render_stacked_widget(
            meta_left,
            label="Ref. del artículo",
            label_class="vf-blue",
            render=lambda target: target.text_input(
                "Ref. del artículo",
                value=selected_id,
                key=_field_key(selected_id, "ref"),
                disabled=True,
                label_visibility="collapsed",
            ),
        )
        tipo_articulo = _render_stacked_widget(
            meta_right,
            label="Tipo de artículo",
            label_class="vf-blue",
            render=lambda target: target.selectbox(
                "Tipo de artículo",
                tipo_articulo_options,
                index=_safe_index(
                    tipo_articulo_options,
                    str(data.get("tipo_articulo") or ""),
                    default=0,
                ),
                key=_field_key(selected_id, "tipo_articulo"),
                label_visibility="collapsed",
            ),
        )
        estado_stock = _render_inline_widget(
            st,
            label="Estado de stock",
            label_class="vf-purple",
            ratio=(0.54, 0.46),
            render=lambda target: target.selectbox(
                "Estado de stock",
                estado_stock_options,
                index=_safe_index(
                    estado_stock_options,
                    str(data.get("estado_stock") or ""),
                    default=0,
                ),
                key=_field_key(selected_id, "estado_stock"),
                label_visibility="collapsed",
            ),
        )
        estado_carga = _render_inline_widget(
            st,
            label="Estado de carga",
            label_class="vf-purple",
            ratio=(0.54, 0.46),
            render=lambda target: target.selectbox(
                "Estado de carga",
                estado_carga_options,
                index=_safe_index(
                    estado_carga_options,
                    str(data.get("estado_carga") or ""),
                    default=0,
                ),
                key=_field_key(selected_id, "estado_carga"),
                label_visibility="collapsed",
            ),
        )
        _close_panel(st)

    with top_main:
        _open_panel(st)
        nombre = _render_stacked_widget(
            st,
            label="Nombre",
            label_class="vf-orange",
            render=lambda target: target.text_input(
                "Nombre",
                value=data.get("nombre") or "",
                key=_field_key(selected_id, "nombre"),
                label_visibility="collapsed",
            ),
        )
        artista = _render_stacked_widget(
            st,
            label="Artista",
            label_class="vf-orange",
            render=lambda target: target.text_input(
                "Artista",
                value=data.get("artista") or "",
                key=_field_key(selected_id, "artista"),
                label_visibility="collapsed",
            ),
        )
        sello = _render_stacked_widget(
            st,
            label="Sello",
            label_class="vf-green",
            render=lambda target: target.text_input(
                "Sello",
                value=data.get("sello") or "",
                key=_field_key(selected_id, "sello"),
                label_visibility="collapsed",
            ),
        )
        generos_col, estilos_col = st.columns(2, gap="small")
        generos = _render_stacked_widget(
            generos_col,
            label="Géneros",
            label_class="vf-cyan",
            render=lambda target: target.text_input(
                "Géneros",
                value=data.get("generos") or "",
                key=_field_key(selected_id, "generos"),
                label_visibility="collapsed",
            ),
        )
        estilos = _render_stacked_widget(
            estilos_col,
            label="Estilos",
            label_class="vf-cyan",
            render=lambda target: target.text_input(
                "Estilos",
                value=data.get("estilos") or "",
                key=_field_key(selected_id, "estilos"),
                label_visibility="collapsed",
            ),
        )
        _close_panel(st)

    with top_extra:
        _open_panel(st)
        año_pais_col, pais_col = st.columns(2, gap="small")
        año = _render_stacked_widget(
            año_pais_col,
            label="Año",
            label_class="vf-green",
            render=lambda target: target.number_input(
                "Año",
                value=normalizar_año(data["año"]) or 0,
                step=1,
                min_value=0,
                key=_field_key(selected_id, "año"),
                label_visibility="collapsed",
            ),
        )
        pais = _render_stacked_widget(
            pais_col,
            label="País",
            label_class="vf-green",
            render=lambda target: target.text_input(
                "País",
                value=data.get("pais") or "",
                key=_field_key(selected_id, "pais"),
                label_visibility="collapsed",
            ),
        )
        duracion_col, peso_col = st.columns(2, gap="small")
        duracion_total = _render_stacked_widget(
            duracion_col,
            label="Duración",
            label_class="vf-cyan",
            render=lambda target: target.text_input(
                "Duración",
                value=data.get("duracion_total") or "",
                key=_field_key(selected_id, "duracion_total"),
                label_visibility="collapsed",
            ),
        )
        estimated_weight = _render_stacked_widget(
            peso_col,
            label="Peso (g)",
            label_class="vf-cyan",
            render=lambda target: target.number_input(
                "Peso (g)",
                value=int(data.get("estimated_weight") or 0),
                step=10,
                min_value=0,
                key=_field_key(selected_id, "estimated_weight"),
                label_visibility="collapsed",
            ),
        )
        precio = _render_stacked_widget(
            st,
            label="Precio (€)",
            label_class="vf-purple",
            render=lambda target: target.number_input(
                "Precio (€)",
                value=float(data.get("precio") or 0.0),
                step=1.0,
                min_value=0.0,
                key=_field_key(selected_id, "precio"),
                label_visibility="collapsed",
            ),
        )
        if data.get("menor_precio") is not None:
            st.markdown(
                f"<div class='vinyl-form-note'>Referencia Discogs: {data['menor_precio']:.2f} $</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div class='vinyl-form-note'>Sin precio mínimo disponible en Discogs.</div>",
                unsafe_allow_html=True,
            )
        _close_panel(st)

    lower_left, lower_center, lower_right = st.columns([0.95, 0.95, 1.9], gap="large")

    with lower_left:
        _open_panel(st)
        estado_disco = _render_stacked_widget(
            st,
            label="Condición del disco",
            label_class="vf-yellow",
            render=lambda target: target.selectbox(
                "Condición del disco",
                estado_disco_options,
                index=_safe_index(
                    estado_disco_options,
                    str(data.get("estado_disco") or ""),
                    default=0,
                ),
                key=_field_key(selected_id, "estado_disco"),
                label_visibility="collapsed",
            ),
        )
        estado_funda = _render_stacked_widget(
            st,
            label="Condición de la funda",
            label_class="vf-yellow",
            render=lambda target: target.selectbox(
                "Condición de la funda",
                estado_funda_options,
                index=_safe_index(
                    estado_funda_options,
                    str(data.get("estado_funda") or ""),
                    default=0,
                ),
                key=_field_key(selected_id, "estado_funda"),
                label_visibility="collapsed",
            ),
        )
        comentarios_estado = _render_stacked_widget(
            st,
            label="Comentarios sobre la conservación",
            label_class="vf-yellow",
            render=lambda target: target.text_area(
                "Comentarios sobre la conservación",
                value=data.get("comentarios_estado") or "",
                height=190,
                key=_field_key(selected_id, "comentarios_estado"),
                label_visibility="collapsed",
            ),
        )
        st.markdown(
            "<div class='vinyl-form-note'>Usa la escala Discogs por separado para el disco y la funda, y añade aquí cualquier matiz del ejemplar.</div>",
            unsafe_allow_html=True,
        )
        _close_panel(st)

    with lower_center:
        _open_panel(st)
        tracklist = _render_stacked_widget(
            st,
            label="Tracklist",
            label_class="vf-steel",
            render=lambda target: target.text_area(
                "Tracklist",
                value=data.get("tracklist") or "",
                height=300,
                key=_field_key(selected_id, "tracklist"),
                label_visibility="collapsed",
            ),
        )
        _close_panel(st)

    with lower_right:
        _open_panel(st)
        notas = _render_stacked_widget(
            st,
            label="Notas",
            label_class="vf-beige",
            render=lambda target: target.text_area(
                "Notas",
                value=data.get("notas") or "",
                height=300,
                key=_field_key(selected_id, "notas"),
                label_visibility="collapsed",
            ),
        )
        st.markdown("<div class='vinyl-form-actions'>", unsafe_allow_html=True)
        st.markdown(
            "<div class='vinyl-form-note'>Revisa la ficha, ajusta el estado y guarda cuando el registro quede listo para exportarse.</div>",
            unsafe_allow_html=True,
        )
        guardar = st.form_submit_button("Guardar cambios", type="primary", width="stretch")
        st.markdown("</div>", unsafe_allow_html=True)
        _close_panel(st)

    st.markdown("</div>", unsafe_allow_html=True)

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
            "estado_disco": estado_disco,
            "estado_funda": estado_funda,
            "comentarios_estado": comentarios_estado,
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
