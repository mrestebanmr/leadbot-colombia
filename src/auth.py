import os
import json
import urllib.parse
import requests
import streamlit as st

AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPES = "https://www.googleapis.com/auth/spreadsheets https://www.googleapis.com/auth/drive.file"
TOKEN_FILE = "config/user_token.json"


def _get_redirect_uri():
    try:
        return str(st.secrets["oauth_credentials"]["redirect_uri"])
    except Exception:
        return os.getenv("OAUTH_REDIRECT_URI", "http://localhost:8501")


def cargar_credenciales_oauth():
    # Intentar leer de st.secrets (producción en Streamlit Cloud)
    try:
        return (
            st.secrets["oauth_credentials"]["client_id"],
            st.secrets["oauth_credentials"]["client_secret"]
        )
    except Exception as e:
        secrets_error = e
    # Fallback: leer del archivo local (desarrollo)
    try:
        with open("config/oauth_credentials.json") as f:
            data = json.load(f)
        return data["web"]["client_id"], data["web"]["client_secret"]
    except FileNotFoundError:
        raise RuntimeError(
            f"No se encontraron credenciales OAuth. "
            f"st.secrets falló con: {secrets_error}. "
            f"Archivo local config/oauth_credentials.json tampoco existe."
        )


def construir_url_oauth(state=None):
    client_id, _ = cargar_credenciales_oauth()
    params = {
        "client_id": client_id,
        "redirect_uri": _get_redirect_uri(),
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",
    }
    if state:
        params["state"] = state
    return AUTHORIZE_URL + "?" + urllib.parse.urlencode(params)


def intercambiar_codigo_por_token(codigo):
    client_id, client_secret = cargar_credenciales_oauth()
    response = requests.post(
        TOKEN_URL,
        data={
            "code": codigo,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": _get_redirect_uri(),
            "grant_type": "authorization_code",
        }
    )
    return response.json()


def guardar_token(token):
    with open(TOKEN_FILE, "w") as f:
        json.dump(token, f)


def cargar_token_guardado():
    try:
        with open(TOKEN_FILE) as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def credenciales_validas():
    return "google_token" in st.session_state
