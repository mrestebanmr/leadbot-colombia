import os
from dotenv import load_dotenv
from outscraper import ApiClient

load_dotenv()

# Leer desde .env en local, desde st.secrets en producción
try:
    import streamlit as st
    OUTSCRAPER_API_KEY = st.secrets.get("OUTSCRAPER_API_KEY") or os.getenv("OUTSCRAPER_API_KEY")
except Exception:
    OUTSCRAPER_API_KEY = os.getenv("OUTSCRAPER_API_KEY")
cliente = ApiClient(api_key=OUTSCRAPER_API_KEY)  # Inicializar cliente Outscraper


class OutscraperAuthError(Exception):
    """La API de Outscraper rechazó la credencial (401) o la cuenta no tiene créditos."""


def _es_error_auth(e):
    msg = str(e)
    return "401" in msg or "403" in msg or "Unauthorized" in msg


def search_businesses(query, language="es", max_leads=20):
    # Verificar que la API Key existe
    if not OUTSCRAPER_API_KEY:
        raise ValueError("Outscraper API Key no encontrada. Revisa el archivo .env o los secrets.")

    # Hacer la búsqueda - limit controla cuantos resultados devuelve
    try:
        resultados = cliente.google_maps_search(
            query,
            limit = max_leads,
            language = language,
            region = "CO"
        )
    except Exception as e:
        if _es_error_auth(e):
            raise OutscraperAuthError(
                "Outscraper rechazó la API key (401). La cuenta puede no tener créditos "
                "disponibles o la key es inválida. Revisa tu saldo en https://app.outscraper.com/profile"
            ) from e
        raise

    # Outscraper devuelve la lista de listas
    empresas = []
    for grupo in resultados:
        for empresa in grupo:
            empresas.append({
                "Nombre": empresa.get("name", "N/A"),
                "Dirección": empresa.get("address", "N/A"),
                "Teléfono": empresa.get("phone", "N/A"),
                "Sitio Web": empresa.get("website", "N/A"),
                "Rating": empresa.get("rating", 0),
                "Reseñas_totales": empresa.get("reviews", 0)
            })

    empresas = enrich_emails(empresas) # Enriquecer con emails (no crítico)
    return empresas


def enrich_emails(empresas):
    # Filtra solo las empresas que tienen sitio web
    con_web = [e for e in empresas if e["Sitio Web"] != "N/A"]

    # Garantizar que todas tengan la columna Email aunque el enriquecimiento falle
    for empresa in empresas:
        empresa.setdefault("Email", "N/A")

    if not con_web:
        return empresas

    # Extrae los dominios de las empresas con Web.
    dominios = [e["Sitio Web"] for e in con_web]

    # Buscar emails para cada dominio. Es un paso lento y secundario:
    # si falla (timeout, 401, etc.) devolvemos los leads igualmente.
    try:
        resultados = cliente.emails_and_contacts(dominios)
    except Exception:
        return empresas

    # Crear diccionario dominio -> email para búsqueda rápida.
    emails_por_dominio = {}
    for resultado in resultados:
        dominio = resultado.get("query", "")
        emails = resultado.get("emails", [])
        if emails:
            emails_por_dominio[dominio] = emails[0].get("value", "N/A")
        else:
            emails_por_dominio[dominio] = "N/A"

    # Añadir email a cada empresa
    for empresa in empresas:
        web = empresa["Sitio Web"]
        empresa["Email"] = emails_por_dominio.get(web, "N/A")

    return empresas
