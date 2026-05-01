import html
import os
import time
from typing import Any

import requests
import streamlit as st

from src.project_meta import get_app_meta

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
APP_META = get_app_meta()
FONT_AWESOME_CSS_URL = (
    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"
)
PAGE_ICON = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 640">
<!--!Font Awesome Free v7.2.0 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2026 Fonticons, Inc.-->
<path d="M64 320C64 178.6 178.6 64 320 64C461.4 64 576 178.6 576 320C576 461.4 461.4 576 320 576C178.6 576 64 461.4 64 320zM320 352C302.3 352 288 337.7 288 320C288 302.3 302.3 288 320 288C337.7 288 352 302.3 352 320C352 337.7 337.7 352 320 352zM224 320C224 373 267 416 320 416C373 416 416 373 416 320C416 267 373 224 320 224C267 224 224 267 224 320zM168 304C168 271.6 184.3 237.4 210.8 210.8C237.3 184.2 271.6 168 304 168C317.3 168 328 157.3 328 144C328 130.7 317.3 120 304 120C256.1 120 210.3 143.5 176.9 176.9C143.5 210.3 120 256.1 120 304C120 317.3 130.7 328 144 328C157.3 328 168 317.3 168 304z"/>
</svg>
"""

# <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 640">
#   <path d="M64 320C64 178.6 178.6 64 320 64C461.4 64 576 178.6 576 320C576 461.4 461.4 576 320 576C178.6 576 64 461.4 64 320zM320 224C373 224 416 267 416 320C416 373 373 416 320 416C267 416 224 373 224 320C224 267 267 224 320 224zM320 464C399.5 464 464 399.5 464 320C464 240.5 399.5 176 320 176C240.5 176 176 240.5 176 320C176 399.5 240.5 464 320 464zM320 352C337.7 352 352 337.7 352 320C352 302.3 337.7 288 320 288C302.3 288 288 302.3 288 320C288 337.7 302.3 352 320 352z"/>
# </svg>




def _as_float(raw: str | None, default: float) -> float:
    try:
        return float(raw) if raw is not None else default
    except (TypeError, ValueError):
        return default


DEFAULT_TIMEOUT_SECONDS = _as_float(os.getenv("API_TIMEOUT_SECONDS"), 30.0)
LONG_TIMEOUT_SECONDS = _as_float(os.getenv("API_LONG_TIMEOUT_SECONDS"), 120.0)


def _inject_frontend_assets() -> None:
    st.markdown(
        f"""
        <link rel="stylesheet" href="{FONT_AWESOME_CSS_URL}">
        <style>
        :root {{
            --mc-inline-icon-gap: 5.92rem;
            --mc-bg: #f6f0e6;
            --mc-bg-soft: #efe4d7;
            --mc-surface: rgba(255, 250, 244, 0.84);
            --mc-surface-strong: rgba(255, 252, 248, 0.96);
            --mc-border: rgba(74, 91, 99, 0.16);
            --mc-border-strong: rgba(74, 91, 99, 0.3);
            --mc-ink: #23323a;
            --mc-muted: #5f6d75;
            --mc-accent: #bb6d47;
            --mc-accent-deep: #9e5637;
            --mc-accent-soft: rgba(187, 109, 71, 0.14);
            --mc-teal: #4f6d70;
            --mc-teal-soft: rgba(79, 109, 112, 0.1);
            --mc-shadow: 0 16px 34px rgba(45, 39, 33, 0.08);
            --mc-shadow-soft: 0 8px 20px rgba(45, 39, 33, 0.05);
        }}
        .stApp {{
            background:
                radial-gradient(circle at top left, rgba(187, 109, 71, 0.08), transparent 24%),
                radial-gradient(circle at top right, rgba(79, 109, 112, 0.1), transparent 22%),
                linear-gradient(180deg, var(--mc-bg) 0%, #f2ece3 100%);
            color: var(--mc-ink);
        }}
        header[data-testid="stHeader"] {{
            background: rgba(246, 240, 230, 0.82);
            backdrop-filter: blur(12px);
        }}
        [data-testid="stDecoration"] {{
            display: none;
        }}
        [data-testid="stSidebarContent"] {{
            background:
                radial-gradient(circle at top, rgba(255, 255, 255, 0.45), transparent 28%),
                linear-gradient(180deg, #eee3d7 0%, #e7dccf 100%);
            border-right: 1px solid var(--mc-border);
        }}
        [data-testid="stSidebarContent"] * {{
            color: var(--mc-ink);
        }}
        [data-testid="stSidebarNav"] a {{
            border-radius: 12px;
            transition: background-color 0.18s ease, color 0.18s ease, box-shadow 0.18s ease;
        }}
        [data-testid="stSidebarNav"] a:hover {{
            background: var(--mc-teal-soft);
            color: var(--mc-teal);
        }}
        [data-testid="stSidebarNav"] a[aria-current="page"] {{
            background: linear-gradient(90deg, rgba(187, 109, 71, 0.18) 0%, rgba(79, 109, 112, 0.1) 100%);
            box-shadow: inset 3px 0 0 var(--mc-accent);
            color: var(--mc-ink);
            font-weight: 700;
        }}
        .block-container,
        [data-testid="stAppViewBlockContainer"] {{
            color: var(--mc-ink);
        }}
        p,
        li,
        label,
        .stMarkdown,
        .stCaption {{
            color: var(--mc-ink);
        }}
        .mc-heading {{
            display: flex;
            align-items: center;
            gap: var(--mc-inline-icon-gap);
            letter-spacing: -0.02em;
            color: var(--mc-ink);
        }}
        .mc-heading i {{
            color: var(--mc-accent);
            min-width: 1.1em;
        }}
        .mc-heading-1 {{
            font-size: clamp(1.8rem, 2vw, 2.4rem);
            margin: 0 0 0.2rem 0;
        }}
        .mc-heading-2 {{
            font-size: 1.35rem;
            margin: 0.25rem 0 0.2rem 0;
        }}
        .mc-heading-3 {{
            font-size: 1.1rem;
            margin: 0.2rem 0 0.15rem 0;
        }}
        .mc-feature-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 0.9rem;
            margin: 1rem 0 1.25rem 0;
        }}
        .mc-feature-card {{
            border: 1px solid var(--mc-border);
            border-radius: 16px;
            padding: 0.9rem 1rem;
            background: var(--mc-surface);
            box-shadow: var(--mc-shadow-soft);
        }}
        .mc-feature-card strong {{
            display: flex;
            align-items: center;
            gap: calc(var(--mc-inline-icon-gap) - 0.12rem);
            color: var(--mc-ink);
            margin-bottom: 0.35rem;
        }}
        .mc-feature-card i {{
            color: var(--mc-accent);
        }}
        .mc-empty-state {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 0.35rem;
            color: var(--mc-muted);
            padding-top: 0.8rem;
        }}
        .mc-empty-state i {{
            font-size: 1.6rem;
            color: var(--mc-teal);
        }}
        .stButton > button,
        div[data-testid="stForm"] button[kind="secondary"] {{
            background: var(--mc-surface-strong);
            border: 1px solid var(--mc-border-strong);
            border-radius: 999px;
            box-shadow: var(--mc-shadow-soft);
            color: var(--mc-ink);
        }}
        .stButton > button:hover,
        div[data-testid="stForm"] button[kind="secondary"]:hover {{
            border-color: rgba(79, 109, 112, 0.42);
            color: var(--mc-teal);
        }}
        div[data-testid="stForm"] button[kind="primary"],
        .stDownloadButton > button {{
            background: linear-gradient(180deg, var(--mc-accent) 0%, var(--mc-accent-deep) 100%);
            border: 1px solid rgba(94, 54, 40, 0.28);
            border-radius: 999px;
            box-shadow: 0 12px 24px rgba(158, 86, 55, 0.18);
            color: #fff;
        }}
        div[data-testid="stForm"] button[kind="primary"]:hover,
        .stDownloadButton > button:hover {{
            background: linear-gradient(180deg, #c87952 0%, #a95d3d 100%);
        }}
        .stTextInput input,
        .stNumberInput input,
        .stTextArea textarea,
        div[data-baseweb="select"] > div,
        [data-testid="stExpander"] {{
            background: var(--mc-surface-strong);
            border-color: var(--mc-border-strong);
        }}
        [data-testid="stExpander"] {{
            border-radius: 14px;
            box-shadow: var(--mc-shadow-soft);
        }}
        [data-testid="stAlert"] {{
            border-radius: 14px;
            border: 1px solid var(--mc-border);
            box-shadow: var(--mc-shadow-soft);
        }}
        .stCaption,
        [data-testid="stMarkdownContainer"] p small {{
            color: var(--mc-muted);
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def configure_page(title: str = "Catálogo de vinilos") -> None:
    try:
        st.set_page_config(page_title=title, page_icon=PAGE_ICON, layout="wide")
    except Exception:
        pass
    _inject_frontend_assets()
    st.sidebar.caption(f"Versión: {APP_META.display_version}")
    if APP_META.changelog_path.exists():
        st.sidebar.caption(f"Cambios: {APP_META.changelog_path.name}")
    show_backend_status(container=st.sidebar)


def render_icon_heading(
    text: str,
    *,
    icon: str,
    level: int = 1,
) -> None:
    safe_text = html.escape(text)
    safe_icon = html.escape(icon)
    level = max(1, min(level, 6))
    st.markdown(
        (
            f'<h{level} class="mc-heading mc-heading-{level}">'
            f'<i class="fa-solid fa-{safe_icon}"></i>'
            f"<span>{safe_text}</span>"
            f"</h{level}>"
        ),
        unsafe_allow_html=True,
    )


def render_icon_cards(cards: list[tuple[str, str, str]]) -> None:
    parts = ['<div class="mc-feature-grid">']
    for icon, title, description in cards:
        parts.append(
            (
                '<div class="mc-feature-card">'
                f'<strong><i class="fa-solid fa-{html.escape(icon)}"></i>'
                f"<span>{html.escape(title)}</span></strong>"
                f"<div>{html.escape(description)}</div>"
                "</div>"
            )
        )
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def render_empty_icon(icon: str, text: str) -> None:
    st.markdown(
        (
            '<div class="mc-empty-state">'
            f'<i class="fa-solid fa-{html.escape(icon)}"></i>'
            f"<div>{html.escape(text)}</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _format_scalar_preview(value: Any, *, max_length: int = 60) -> str:
    if value is None:
        text = "null"
    elif isinstance(value, bool):
        text = "true" if value else "false"
    else:
        text = str(value).strip()

    compact = " ".join(text.split())
    if len(compact) <= max_length:
        return compact
    return f"{compact[: max_length - 1].rstrip()}..."


def _object_preview(mapping: dict[str, Any]) -> str | None:
    for key in ("title", "name", "resource_url", "position", "type", "catno", "id"):
        value = mapping.get(key)
        preview = _format_scalar_preview(value)
        if preview and preview != "null":
            return preview
    return None


def _node_summary(value: Any) -> str:
    if isinstance(value, dict):
        count = len(value)
        suffix = "campo" if count == 1 else "campos"
        preview = _object_preview(value)
        if preview:
            return f"{count} {suffix} - {preview}"
        return f"{count} {suffix}"

    if isinstance(value, list):
        count = len(value)
        suffix = "elemento" if count == 1 else "elementos"
        if count == 0:
            return f"0 {suffix}"
        first = value[0]
        if isinstance(first, dict):
            preview = _object_preview(first)
            if preview:
                return f"{count} {suffix} - {preview}"
        elif not isinstance(first, (dict, list)):
            preview = _format_scalar_preview(first, max_length=36)
            if preview:
                return f"{count} {suffix} - {preview}"
        return f"{count} {suffix}"

    return _format_scalar_preview(value)


def _list_item_label(index: int, value: Any) -> str:
    base = f"[{index}]"
    if isinstance(value, dict):
        preview = _object_preview(value)
        if preview:
            return f"{base} - {preview}"
    elif not isinstance(value, (dict, list)):
        preview = _format_scalar_preview(value, max_length=42)
        if preview:
            return f"{base} - {preview}"
    return base


def _render_leaf_row(label: str, value: Any, *, container: Any) -> None:
    left_col, right_col = container.columns([0.3, 0.7], gap="small")
    left_col.caption(label)
    if value is None:
        right_col.caption("null")
    elif isinstance(value, bool):
        right_col.write("true" if value else "false")
    elif isinstance(value, str) and "\n" in value:
        right_col.text(value)
    else:
        right_col.write(value)


def _render_tree_children(value: Any, *, container: Any, expand_all: bool) -> None:
    if isinstance(value, dict):
        if not value:
            container.caption("Objeto vacio")
            return
        for child_label, child_value in value.items():
            _render_tree_entry(str(child_label), child_value, container=container, expand_all=expand_all, top_level=False)
        return

    if isinstance(value, list):
        if not value:
            container.caption("Lista vacia")
            return
        if all(not isinstance(item, (dict, list)) for item in value):
            for index, item in enumerate(value, start=1):
                _render_leaf_row(f"[{index}]", item, container=container)
            return
        for index, item in enumerate(value, start=1):
            _render_tree_entry(_list_item_label(index, item), item, container=container, expand_all=expand_all, top_level=False)
        return

    container.write(value)


def _render_tree_entry(
    label: str,
    value: Any,
    *,
    container: Any,
    expand_all: bool,
    top_level: bool,
) -> None:
    if top_level or isinstance(value, (dict, list)):
        expander = container.expander(f"{label} ({_node_summary(value)})", expanded=expand_all)
        _render_tree_children(value, container=expander, expand_all=expand_all)
        return

    _render_leaf_row(label, value, container=container)


def render_nested_data_tree(
    data: Any,
    *,
    state_key: str,
) -> None:
    expand_key = f"{state_key}_expand_all"
    if expand_key not in st.session_state:
        st.session_state[expand_key] = False

    action_left, action_right = st.columns([1, 1], gap="small")
    with action_left:
        if st.button("Desplegar todo", key=f"{state_key}_expand_button", width="stretch"):
            st.session_state[expand_key] = True
    with action_right:
        if st.button("Colapsar todo", key=f"{state_key}_collapse_button", width="stretch"):
            st.session_state[expand_key] = False

    st.caption("Vista estructurada de la respuesta de Discogs")
    expand_all = bool(st.session_state.get(expand_key, False))

    if isinstance(data, dict):
        entries = list(data.items())
        chunk_size = (len(entries) + 2) // 3
        first_entries = entries[:chunk_size]
        second_entries = entries[chunk_size : chunk_size * 2]
        third_entries = entries[chunk_size * 2 :]

        first_col, second_col, third_col = st.columns(3, gap="large")
        for label, value in first_entries:
            _render_tree_entry(str(label), value, container=first_col, expand_all=expand_all, top_level=True)
        for label, value in second_entries:
            _render_tree_entry(str(label), value, container=second_col, expand_all=expand_all, top_level=True)
        for label, value in third_entries:
            _render_tree_entry(str(label), value, container=third_col, expand_all=expand_all, top_level=True)
        return

    if isinstance(data, list):
        for index, value in enumerate(data, start=1):
            _render_tree_entry(_list_item_label(index, value), value, container=st, expand_all=expand_all, top_level=True)
        return

    st.write(data)


def _url(path: str) -> str:
    return f"{API_URL}{path}"


def api_get(path: str, *, timeout: float | None = DEFAULT_TIMEOUT_SECONDS, **kwargs) -> Any:
    response = requests.get(_url(path), timeout=timeout, **kwargs)
    response.raise_for_status()
    return response.json()


def api_get_bytes(path: str, *, timeout: float | None = DEFAULT_TIMEOUT_SECONDS, **kwargs) -> bytes:
    response = requests.get(_url(path), timeout=timeout, **kwargs)
    response.raise_for_status()
    return response.content


def api_post(path: str, *, timeout: float | None = DEFAULT_TIMEOUT_SECONDS, **kwargs) -> Any:
    response = requests.post(_url(path), timeout=timeout, **kwargs)
    response.raise_for_status()
    return response.json()


def api_put(path: str, *, timeout: float | None = DEFAULT_TIMEOUT_SECONDS, **kwargs) -> Any:
    response = requests.put(_url(path), timeout=timeout, **kwargs)
    response.raise_for_status()
    return response.json()


def show_backend_status(*, container: Any | None = None) -> None:
    target = container or st
    last_exc: Exception | None = None
    for attempt in range(8):
        try:
            api_get("/health", timeout=3.0)
            target.success(f"Backend activo: {API_URL}")
            return
        except Exception as exc:
            last_exc = exc
            if attempt < 7:
                time.sleep(0.35)

    target.error(f"Backend no disponible: {API_URL} ({last_exc})")
