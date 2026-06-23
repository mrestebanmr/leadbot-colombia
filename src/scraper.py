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

def search_businesses(query, language="es", max_leads=20):
    # Verificar que la API Key existe
    if not OUTSCRAPER_API_KEY:
        raise ValueError("Outscraper API Key no encontrada. Revisa el archivo .env")

    # Hacer la búsqueda - limit controla cuantos resultados devuelve
    resultados = cliente.google_maps_search(
        query,
        limit = max_leads,
        language = language,
        region = "CO"
    )

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

    empresas = enrich_emails(empresas) # Enriquecer con emails
    return empresas

def enrich_emails(empresas):
    # Filtra solo las empresas que tienen sitio web
    con_web = [e for e in empresas if e["Sitio Web"] != "N/A"]

    if not con_web:
        return empresas

    # Extrae los dominios de las empresas con Web.
    dominios = [e["Sitio Web"] for e in con_web]

    # Buscar emails para cada dominio
    resultados = cliente.emails_and_contacts(dominios)

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
