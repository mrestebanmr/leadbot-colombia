import os
import time
import requests
from dotenv import load_dotenv
from outscraper import ApiClient

load_dotenv()

# Leer desde .env en local, desde st.secrets en producción
try:
    import streamlit as st
    OUTSCRAPER_API_KEY = st.secrets.get("OUTSCRAPER_API_KEY") or os.getenv("OUTSCRAPER_API_KEY")
except Exception:
    OUTSCRAPER_API_KEY = os.getenv("OUTSCRAPER_API_KEY")

# Cliente del SDK solo para el enriquecimiento de emails (paso secundario).
cliente = ApiClient(api_key=OUTSCRAPER_API_KEY)

# La búsqueda principal NO usa el SDK: su endpoint síncrono (/google-maps-search)
# devuelve 504 con frecuencia y deja la app colgada. Usamos el endpoint asíncrono
# /maps/search-v2 con polling propio, que es estable, y controlamos timeouts y
# reintentos para que la búsqueda nunca se quede colgada indefinidamente.
_BASE_URL = "https://api.app.outscraper.com"
_REINTENTOS = 8                 # reintentos ante errores transitorios
_CODIGOS_REINTENTABLES = {401, 403, 429, 500, 502, 503, 504}
_MAX_ESPERA_RESULTADO = 240     # segundos máximos esperando el resultado (polling)


class OutscraperAuthError(Exception):
    """Outscraper rechazó la petición de forma persistente (key, créditos o límite temporal)."""


def _peticion(session, url, params=None):
    """GET con reintentos ante errores transitorios (401/5xx) y caídas de conexión."""
    ultimo = None
    for intento in range(_REINTENTOS):
        try:
            r = session.get(url, params=params, timeout=40)
            if r.status_code < 400:
                return r
            ultimo = f"HTTP {r.status_code}"
            if r.status_code not in _CODIGOS_REINTENTABLES:
                r.raise_for_status()
        except requests.exceptions.RequestException as e:
            ultimo = f"conexión ({type(e).__name__})"
        time.sleep(min(2 * (intento + 1), 12))  # backoff progresivo

    raise OutscraperAuthError(
        f"Outscraper no respondió correctamente tras {_REINTENTOS} intentos ({ultimo}). "
        "Puede ser un límite temporal de la cuenta, falta de créditos o una key inválida. "
        "Revisa tu saldo en https://app.outscraper.com/profile e inténtalo de nuevo en unos minutos."
    )


def search_businesses(query, language="es", max_leads=20):
    if not OUTSCRAPER_API_KEY:
        raise ValueError("Outscraper API Key no encontrada. Revisa el archivo .env o los secrets.")

    session = requests.Session()
    session.headers.update({"X-API-KEY": OUTSCRAPER_API_KEY})

    # 1) Enviar la tarea de búsqueda (endpoint asíncrono)
    submit = _peticion(session, f"{_BASE_URL}/maps/search-v2", params={
        "query": query,
        "limit": max_leads,
        "language": language,
        "region": "CO",
    })
    results_location = submit.json().get("results_location")
    if not results_location:
        # Respuesta síncrona (algunos casos devuelven los datos directamente)
        data = submit.json().get("data")
        return _parsear(data)

    # 2) Polling hasta que la tarea termine (con tope de tiempo)
    inicio = time.time()
    while time.time() - inicio < _MAX_ESPERA_RESULTADO:
        time.sleep(5)
        estado = _peticion(session, results_location).json()
        if estado.get("status") and estado["status"] != "Pending":
            return _parsear(estado.get("data"))

    raise OutscraperAuthError(
        "La búsqueda tardó demasiado en Outscraper y se canceló. Inténtalo de nuevo."
    )


def _parsear(data):
    """Convierte la respuesta de Outscraper en la lista de empresas que usa la app."""
    if not data:
        return []
    # data puede venir como lista de listas (una por query) o lista plana
    grupos = data if isinstance(data[0], list) else [data]

    empresas = []
    for grupo in grupos:
        for e in grupo:
            empresas.append({
                "Nombre": e.get("name") or "N/A",
                "Dirección": e.get("full_address") or e.get("address") or "N/A",
                "Teléfono": e.get("phone") or e.get("phone_number") or "N/A",
                "Sitio Web": e.get("site") or e.get("website") or "N/A",
                "Rating": e.get("rating") or 0,
                "Reseñas_totales": e.get("reviews") if e.get("reviews") is not None else e.get("reviews_count", 0),
            })

    return enrich_emails(empresas)


def enrich_emails(empresas):
    # Garantizar la columna Email aunque el enriquecimiento falle
    for empresa in empresas:
        empresa.setdefault("Email", "N/A")

    con_web = [e for e in empresas if e["Sitio Web"] != "N/A"]
    if not con_web:
        return empresas

    dominios = [e["Sitio Web"] for e in con_web]

    # Paso lento y secundario: si falla (timeout, límite, etc.) devolvemos los leads igual.
    try:
        resultados = cliente.emails_and_contacts(dominios)
    except Exception:
        return empresas

    emails_por_dominio = {}
    for resultado in resultados:
        dominio = resultado.get("query", "")
        emails = resultado.get("emails", [])
        emails_por_dominio[dominio] = emails[0].get("value", "N/A") if emails else "N/A"

    for empresa in empresas:
        empresa["Email"] = emails_por_dominio.get(empresa["Sitio Web"], "N/A")

    return empresas
