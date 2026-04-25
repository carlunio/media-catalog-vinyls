import os
import time
from typing import Any

import requests
import streamlit as st

from src.project_meta import get_app_meta

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
APP_META = get_app_meta()


def _as_float(raw: str | None, default: float) -> float:
    try:
        return float(raw) if raw is not None else default
    except (TypeError, ValueError):
        return default


DEFAULT_TIMEOUT_SECONDS = _as_float(os.getenv("API_TIMEOUT_SECONDS"), 30.0)
LONG_TIMEOUT_SECONDS = _as_float(os.getenv("API_LONG_TIMEOUT_SECONDS"), 120.0)


def configure_page(title: str = "Catálogo de vinilos") -> None:
    try:
        st.set_page_config(page_title=title, layout="wide")
    except Exception:
        pass
    st.sidebar.caption(f"Versión: {APP_META.display_version}")


def get_app_version_label() -> str:
    return APP_META.display_version


def get_changelog_path() -> str | None:
    if APP_META.changelog_path.exists():
        return str(APP_META.changelog_path)
    return None


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
