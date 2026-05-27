import html
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

GRADING_GUIDE_URL = "https://support.discogs.com/hc/en-us/articles/360001566193-How-To-Grade-Items"
TC_SECTION_MAX_LEVELS = 8


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


def _tc_condition_options(allowed_values, current):
    base = [str(item).strip() for item in allowed_values.get("estado_tc", []) if str(item).strip()]
    options = []
    for item in base or ["5", "4", "3", "2", "1"]:
        if item not in options:
            options.append(item)
    current_value = str(current or "").strip()
    if current_value and current_value not in options:
        options.append(current_value)
    options.append("")
    return options


def _field_key(record_id, field):
    return f"vinilo_revision_{record_id}_{field}"


def _display_text(value):
    text = str(value or "").strip()
    if text.lower() in {"none", "null", "nan"}:
        return ""
    return text


def _normalize_tc_section_value(value):
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else None

    text = _display_text(value)
    if not text:
        return None
    return text


def _tc_section_state_key(record_id, suffix):
    return _field_key(record_id, f"tc_section_{suffix}")


def _build_tc_sections_index(payload):
    nodes_payload = payload.get("nodes") if isinstance(payload, dict) else []
    nodes = []
    for raw_node in nodes_payload if isinstance(nodes_payload, list) else []:
        if not isinstance(raw_node, dict):
            continue

        node_key = _display_text(raw_node.get("node_key"))
        label = _display_text(raw_node.get("label"))
        if not node_key or not label:
            continue

        path_labels = [str(item).strip() for item in raw_node.get("path_labels") or [] if str(item).strip()]
        path_keys = [str(item).strip() for item in raw_node.get("path_keys") or [] if str(item).strip()]
        try:
            depth = int(raw_node.get("depth") or 0)
        except (TypeError, ValueError):
            depth = 0
        try:
            sort_order = int(raw_node.get("sort_order") or 0)
        except (TypeError, ValueError):
            sort_order = 0

        node = {
            "node_key": node_key,
            "parent_key": _display_text(raw_node.get("parent_key")) or None,
            "section_id": _normalize_tc_section_value(raw_node.get("section_id")),
            "label": label,
            "depth": depth,
            "path_labels": path_labels,
            "path_keys": path_keys,
            "path_text": _display_text(raw_node.get("path_text")) or " > ".join(path_labels),
            "display_path": _display_text(raw_node.get("display_path"))
            or " > ".join(path_labels[1:] if len(path_labels) > 1 else path_labels),
            "is_leaf": bool(raw_node.get("is_leaf")),
            "sort_order": sort_order,
        }
        nodes.append(node)

    nodes.sort(key=lambda node: (node["depth"], node["sort_order"], node["display_path"]))
    nodes_by_key = {node["node_key"]: node for node in nodes}
    children_by_parent = {}
    leaf_by_section_id = {}
    for node in nodes:
        children_by_parent.setdefault(node["parent_key"], []).append(node)
        if node["is_leaf"] and node["section_id"] is not None:
            leaf_by_section_id[node["section_id"]] = node

    root_key = _display_text(payload.get("root_key")) if isinstance(payload, dict) else ""
    if not root_key:
        root_key = next((node["node_key"] for node in nodes if node["depth"] == 0), "")

    return {
        "nodes": nodes,
        "nodes_by_key": nodes_by_key,
        "children_by_parent": children_by_parent,
        "leaf_by_section_id": leaf_by_section_id,
        "root_key": root_key or None,
    }


def _sync_tc_section_state(record_id, current_section_id, sections_index):
    keys = {
        "value": _tc_section_state_key(record_id, "value"),
        "path": _tc_section_state_key(record_id, "path"),
        "source": _tc_section_state_key(record_id, "source"),
    }
    normalized_current = _normalize_tc_section_value(current_section_id)
    if st.session_state.get(keys["source"]) == normalized_current:
        return

    leaf_node = sections_index["leaf_by_section_id"].get(normalized_current)
    st.session_state[keys["value"]] = normalized_current if leaf_node else None
    st.session_state[keys["path"]] = list((leaf_node or {}).get("path_keys") or [])[1:]
    st.session_state[keys["source"]] = normalized_current


def _get_tc_section_value(record_id):
    return _normalize_tc_section_value(st.session_state.get(_tc_section_state_key(record_id, "value")))


def _sync_tc_section_from_pickers(record_id, sections_index):
    path_state_key = _tc_section_state_key(record_id, "path")
    value_state_key = _tc_section_state_key(record_id, "value")
    parent_key = sections_index["root_key"]
    new_path = []
    selected_leaf_id = None

    for level in range(TC_SECTION_MAX_LEVELS):
        children = sections_index["children_by_parent"].get(parent_key, [])
        if not children:
            break

        widget_key = _tc_section_state_key(record_id, f"picker_{level}")
        if widget_key not in st.session_state:
            break

        choice = _display_text(st.session_state.get(widget_key))
        if not choice:
            break

        valid_choices = {child["node_key"] for child in children}
        if choice not in valid_choices:
            break

        new_path.append(choice)
        node = sections_index["nodes_by_key"][choice]
        parent_key = choice
        if node["is_leaf"]:
            selected_leaf_id = node["section_id"]
            break

    st.session_state[path_state_key] = new_path
    st.session_state[value_state_key] = selected_leaf_id

    clear_from = len(new_path) if new_path else 1
    for stale_level in range(clear_from, TC_SECTION_MAX_LEVELS):
        stale_key = _tc_section_state_key(record_id, f"picker_{stale_level}")
        if stale_level == 0:
            continue
        st.session_state.pop(stale_key, None)


def _render_tc_section_selector(container, record_id, sections_index):
    if not sections_index["nodes"] or not sections_index["root_key"]:
        container.warning("No se han podido cargar las secciones de Todocolección.")
        return

    path_state_key = _tc_section_state_key(record_id, "path")
    value_state_key = _tc_section_state_key(record_id, "value")
    selected_section_id = _get_tc_section_value(record_id)

    with container.popover(
        f"Sección Todocolección · {selected_section_id}"
        if selected_section_id
        else "Sección Todocolección",
        use_container_width=True,
    ):
        stored_path = list(st.session_state.get(path_state_key) or [])
        parent_key = sections_index["root_key"]
        new_path = []
        selected_leaf_id = None

        for level in range(TC_SECTION_MAX_LEVELS):
            children = sections_index["children_by_parent"].get(parent_key, [])
            if not children:
                break

            option_keys = [""] + [child["node_key"] for child in children]
            default_key = ""
            if level < len(stored_path) and stored_path[level] in option_keys:
                default_key = stored_path[level]

            widget_key = _tc_section_state_key(record_id, f"picker_{level}")
            if st.session_state.get(widget_key) not in option_keys:
                st.session_state[widget_key] = default_key

            choice = st.selectbox(
                f"Sección {level + 1}",
                option_keys,
                key=widget_key,
                on_change=_sync_tc_section_from_pickers,
                args=(record_id, sections_index),
                format_func=lambda value, current_level=level: (
                    "Sin sección" if current_level == 0 and not value else "Selecciona..."
                    if not value
                    else sections_index["nodes_by_key"][value]["label"]
                ),
                label_visibility="collapsed",
            )
            if not choice:
                break

            new_path.append(choice)
            node = sections_index["nodes_by_key"][choice]
            parent_key = choice
            if node["is_leaf"]:
                selected_leaf_id = node["section_id"]
                break

        st.session_state[path_state_key] = new_path
        st.session_state[value_state_key] = selected_leaf_id


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
            align-items: center;
            border: 1px solid rgba(77, 70, 62, 0.22);
            border-radius: 10px;
            color: #22313a;
            display: flex;
            font-size: 0.96rem;
            font-weight: 700;
            gap: 0.5rem;
            justify-content: space-between;
            line-height: 1.1rem;
            margin-bottom: 0.34rem;
            padding: 0.45rem 0.58rem;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.22);
        }
        .vinyl-form-label-link {
            color: #22313a;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            text-decoration: none;
        }
        .vinyl-form-label-link:hover {
            color: #9e5637;
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
        .vinyl-form-panel div[data-baseweb="select"] > div,
        .vinyl-form-panel input,
        .vinyl-form-panel textarea {
            background: rgba(255, 252, 248, 0.96);
            border-color: rgba(94, 84, 74, 0.28);
            border-radius: 12px;
        }
        .vinyl-form-panel input:disabled,
        .vinyl-form-panel textarea:disabled {
            background: rgba(241, 236, 229, 0.96) !important;
            color: #6a757d !important;
        }
        .vinyl-form-panel .stButton > button[kind="primary"] {
            background: linear-gradient(180deg, var(--mc-accent, #bb6d47), var(--mc-accent-deep, #9e5637));
            border: 1px solid rgba(94, 54, 40, 0.28);
            box-shadow: 0 12px 24px rgba(158, 86, 55, 0.18);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_label(container, label, label_class, *, help_url=None, help_label=None, help_text=None):
    safe_label = html.escape(str(label))
    safe_label_class = html.escape(str(label_class))
    help_html = ""
    if help_url:
        safe_help_url = html.escape(str(help_url), quote=True)
        safe_help_label = html.escape(str(help_label or "Abrir ayuda"), quote=True)
        help_html = (
            f"<a class='vinyl-form-label-link' href='{safe_help_url}' "
            f"target='_blank' rel='noopener noreferrer' aria-label='{safe_help_label}' "
            f"title='{safe_help_label}'><i class='fa-solid fa-circle-info'></i></a>"
        )
    elif help_text:
        safe_help_text = html.escape(str(help_text), quote=True)
        help_html = (
            f"<span class='vinyl-form-label-link' role='button' tabindex='0' "
            f"aria-label='{safe_help_text}' title='{safe_help_text}'>"
            "<i class='fa-solid fa-circle-info'></i></span>"
        )
    container.markdown(
        f"<div class='vinyl-form-label {safe_label_class}'><span>{safe_label}</span>{help_html}</div>",
        unsafe_allow_html=True,
    )


def _render_inline_widget(
    container,
    *,
    label,
    label_class,
    ratio=(0.36, 0.64),
    render,
    help_url=None,
    help_label=None,
    help_text=None,
):
    left_col, right_col = container.columns([ratio[0], ratio[1]], gap="small")
    _render_label(left_col, label, label_class, help_url=help_url, help_label=help_label, help_text=help_text)
    return render(right_col)


def _render_stacked_widget(
    container,
    *,
    label,
    label_class,
    render,
    help_url=None,
    help_label=None,
    help_text=None,
):
    _render_label(container, label, label_class, help_url=help_url, help_label=help_label, help_text=help_text)
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
tc_sections_index = _build_tc_sections_index(
    options_payload.get("tc_sections") if isinstance(options_payload, dict) else {}
)

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

_sync_tc_section_state(selected_id, data.get("tc_section"), tc_sections_index)

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
estado_tc_options = _tc_condition_options(allowed_values, data.get("estado_tc"))
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
        label="Formato",
        label_class="vf-blue",
        render=lambda target: target.text_input(
            "Formato",
            value=data.get("tipo_articulo") or "",
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
    _render_tc_section_selector(st, selected_id, tc_sections_index)
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
        help_url=GRADING_GUIDE_URL,
        help_label="Abrir guía de graduación de Discogs en otra pestaña",
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
        help_url=GRADING_GUIDE_URL,
        help_label="Abrir guía de graduación de Discogs en otra pestaña",
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
    estado_tc = _render_stacked_widget(
        st,
        label="Estado TC",
        label_class="vf-yellow",
        help_text="5 Muy bueno; 4 Bueno; 3 Normal; 2 Algún defecto; 1 Defectuoso.",
        render=lambda target: target.selectbox(
            "Estado TC",
            estado_tc_options,
            index=_safe_index(
                estado_tc_options,
                str(data.get("estado_tc") or ""),
                default=len(estado_tc_options) - 1,
            ),
            key=_field_key(selected_id, "estado_tc"),
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
        "<div class='vinyl-form-note'>Usa la escala Discogs para disco y funda; Estado TC es el valor 1-5 que se exporta a Todocolección.</div>",
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
    creditos = _render_stacked_widget(
        st,
        label="Créditos",
        label_class="vf-steel",
        render=lambda target: target.text_area(
            "Créditos",
            value=data.get("creditos") or "",
            height=190,
            key=_field_key(selected_id, "creditos"),
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
    guardar = st.button("Guardar cambios", type="primary", width="stretch")
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
        "creditos": creditos,
        "estado_disco": estado_disco,
        "estado_funda": estado_funda,
        "comentarios_estado": comentarios_estado,
        "estado_tc": estado_tc,
        "precio": precio,
        "estado_carga": estado_carga,
        "estado_stock": estado_stock,
        "notas": notas,
        "tc_section": _get_tc_section_value(selected_id),
    }

    try:
        api_put(f"/vinilos/{selected_id}", json=payload)
        st.success("Ficha actualizada correctamente")
    except Exception as exc:
        st.error(f"No se pudo actualizar la ficha: {exc}")
