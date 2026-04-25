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
PAGE_ICON = ":material/album:"


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
        .mc-heading {{
            display: flex;
            align-items: center;
            gap: 0.6rem;
            letter-spacing: -0.02em;
        }}
        .mc-heading i {{
            color: #3a6278;
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
            border: 1px solid rgba(58, 98, 120, 0.16);
            border-radius: 14px;
            padding: 0.9rem 1rem;
            background: rgba(250, 252, 253, 0.92);
        }}
        .mc-feature-card strong {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            color: #27485a;
            margin-bottom: 0.35rem;
        }}
        .mc-feature-card i {{
            color: #3a6278;
        }}
        .mc-empty-state {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 0.35rem;
            color: #6c7a84;
            padding-top: 0.8rem;
        }}
        .mc-empty-state i {{
            font-size: 1.6rem;
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


def get_app_version_label() -> str:
    return APP_META.display_version


def get_changelog_path() -> str | None:
    if APP_META.changelog_path.exists():
        return str(APP_META.changelog_path)
    return None


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


def show_backend_status() -> None:
    last_exc: Exception | None = None
    for attempt in range(8):
        try:
            api_get("/health", timeout=3.0)
            st.success(f"Backend activo: {API_URL}")
            return
        except Exception as exc:
            last_exc = exc
            if attempt < 7:
                time.sleep(0.35)

    st.error(f"Backend no disponible: {API_URL} ({last_exc})")
