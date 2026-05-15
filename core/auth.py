"""
core/auth.py
Sistema de autenticación con bcrypt + Google Sheets.
"""
import streamlit as st
import bcrypt
import pandas as pd
from typing import Optional
from core.sheets import read_worksheet, append_row, invalidate_cache, get_worksheet
from core.config import WS_USERS


def hash_password(plain_password: str) -> str:
    """Hashea una contraseña con bcrypt."""
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed: str) -> bool:
    """Verifica una contraseña contra su hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def get_user(username: str) -> Optional[dict]:
    """Busca un usuario por username en la worksheet Usuarios."""
    df = read_worksheet(WS_USERS)
    if df.empty:
        return None
    match = df[df["username"].str.lower() == username.lower()]
    if match.empty:
        return None
    user = match.iloc[0].to_dict()
    if str(user.get("activo", "")).upper() not in ("TRUE", "VERDADERO", "SI", "1"):
        return None
    return user


def login(username: str, password: str) -> tuple[bool, str]:
    """
    Intenta autenticar. Devuelve (success, message).
    Si success=True, guarda en session_state.
    """
    if not username or not password:
        return False, "Ingresa usuario y contraseña."

    user = get_user(username)
    if not user:
        return False, "Usuario no encontrado o inactivo."

    if not verify_password(password, user.get("password_hash", "")):
        return False, "Contraseña incorrecta."

    st.session_state["auth_user"] = {
        "username": user["username"],
        "nombre_completo": user["nombre_completo"],
        "rol": user["rol"],
    }
    return True, "OK"


def logout():
    """Cierra sesión."""
    for key in list(st.session_state.keys()):
        if key.startswith("auth_") or key == "current_module":
            del st.session_state[key]


def is_authenticated() -> bool:
    """True si hay usuario autenticado en sesión."""
    return "auth_user" in st.session_state


def current_user() -> Optional[dict]:
    """Devuelve el dict del usuario autenticado, o None."""
    return st.session_state.get("auth_user")


def current_user_display_name() -> str:
    """Nombre para mostrar del usuario autenticado."""
    user = current_user()
    if not user:
        return ""
    return user.get("nombre_completo", user.get("username", ""))


def seed_initial_users() -> str:
    """
    Crea los usuarios iniciales Sofi y Evelyn si no existen.
    Llama a esto desde una página admin oculta o en el primer arranque.
    """
    df = read_worksheet(WS_USERS)
    existing_usernames = set()
    if not df.empty and "username" in df.columns:
        existing_usernames = set(df["username"].str.lower())

    initial = st.secrets.get("initial_users", {})
    sofi_pwd = initial.get("sofi_password", "STT_Sofi_2026!")
    evelyn_pwd = initial.get("evelyn_password", "STT_Evelyn_2026!")

    created = []

    if "sofi" not in existing_usernames:
        append_row(WS_USERS, [
            "sofi",
            hash_password(sofi_pwd),
            "Sofia Morataya",
            "Supervisora",
            "TRUE",
        ])
        created.append("sofi")

    if "evelyn" not in existing_usernames:
        append_row(WS_USERS, [
            "evelyn",
            hash_password(evelyn_pwd),
            "Evelyn",
            "Manager",
            "TRUE",
        ])
        created.append("evelyn")

    if not created:
        return "Usuarios ya existen, no se creó nada."
    return f"Creados: {', '.join(created)}"
