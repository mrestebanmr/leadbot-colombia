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

# La búsqueda usa el endpoint "tiempo real" (síncrono) de Outscraper: devuelve los
# resultados en segundos, igual que hacía LeadBot Italia. NO usamos la cola asíncrona
# del nivel gratuito (que puede tardar hasta 1 hora). Llamamos al endpoint directamente
# en vez de via SDK para poder fijar un TIMEOUT (que el SDK no expone) y así garantizar
# que la búsqueda nunca deje la app colgada, además de reintentar ante blips puntuales.
_BASE_URL = "https://api.app.outscraper.com"
_SEARCH_PATH = "/google-maps-search"
_TIMEOUT = 90                                  # segundos por petición
_REINTENTOS = 4                                # reintentos ante errores transitorios
_CODIGOS_REINTENTABLES = {429, 500, 502, 503, 504}


class OutscraperAuthError(Exception):
    """Outscraper rechazó la petición (key inválida, sin créditos o límite temporal)."""


def search_businesses(query, language="es", max_leads=20):
    if not OUTSCRAPER_API_KEY:
        raise ValueError("Outscraper API Key no encontrada. Revisa el archivo .env o los secrets.")

    payload = {
        "query": [query],
        "language": language,
        "region": "CO",
        "organizationsPerQueryLimit": max_leads,
        "async": False,                        # tiempo real: respuesta inmediata
    }
    headers = {"X-API-KEY": OUTSCRAPER_API_KEY, "Content-Type": "application/json"}

    ultimo = None
    for intento in range(_REINTENTOS):
        try:
            r = requests.post(
                f"{_BASE_URL}{_SEARCH_PATH}", json=payload, headers=headers, timeout=_TIMEOUT
            )
            if r.status_code in (401, 403):
                raise OutscraperAuthError(
                    "Outscraper rechazó la API key (401/403). Puede ser una key inválida, "
                    "falta de créditos o un límite temporal de la cuenta. Revisa tu saldo en "
                    "https://app.outscraper.com/profile e inténtalo de nuevo en unos minutos."
                )
            if r.status_code in _CODIGOS_REINTENTABLES:
                ultimo = f"HTTP {r.status_code}"
                time.sleep(2 * (intento + 1))
                continue
            r.raise_for_status()
            data = r.json().get("data", [])
            return _parsear(data)
        except requests.exceptions.RequestException as e:
            ultimo = f"conexión ({type(e).__name__})"
            time.sleep(2 * (intento + 1))

    raise OutscraperAuthError(
        f"Outscraper no respondió tras {_REINTENTOS} intentos ({ultimo}). "
        "Inténtalo de nuevo en unos minutos."
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
                "Dirección": e.get("address") or e.get("full_address") or "N/A",
                "Teléfono": e.get("phone") or e.get("phone_number") or "N/A",
                "Sitio Web": e.get("website") or e.get("site") or "N/A",
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
