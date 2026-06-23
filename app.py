import os
import uuid
import streamlit as st
import pickle
from dotenv import load_dotenv
import plotly.express as px
import plotly.graph_objects as go
from src.scraper import search_businesses
from src.cleaner import limpiar_datos
from src.exporter import exportar_google_sheets
from src.auth import (
    credenciales_validas,
    construir_url_oauth,
    intercambiar_codigo_por_token,
    guardar_token,
    cargar_token_guardado,
)

load_dotenv()
# Leer secrets de Streamlit Cloud si están disponibles
if hasattr(st, "secrets"):
    os.environ.setdefault("GOOGLE_MAPS_API_KEY", st.secrets.get("GOOGLE_MAPS_API_KEY", ""))
    os.environ.setdefault("OUTSCRAPER_API_KEY", st.secrets.get("OUTSCRAPER_API_KEY", ""))
    os.environ.setdefault("GOOGLE_SHEET_ID", st.secrets.get("GOOGLE_SHEET_ID", ""))

# --- Cargar token guardado al inicio ---
if "google_token" not in st.session_state:
    token_guardado = cargar_token_guardado()
    if token_guardado:
        st.session_state.google_token = token_guardado

# --- Capturar código OAuth si Google redirigió aquí (mismo tab) ---
params = st.query_params
if "code" in params and not credenciales_validas():
    try:
        token = intercambiar_codigo_por_token(params["code"])
        if "access_token" in token:
            guardar_token(token)
            st.session_state.google_token = token

            # Restaurar df y query guardados antes del redirect
            state_id = params.get("state", "")
            state_file = f"/tmp/oauth_state_{state_id}.pkl"
            if state_id and os.path.exists(state_file):
                with open(state_file, "rb") as f:
                    saved = pickle.load(f)
                st.session_state.df = saved["df"]
                st.session_state.ultimo_query = saved["query"]
                st.session_state.auto_export = True
                os.remove(state_file)

            st.query_params.clear()
            st.rerun()
        else:
            st.error(f"Error OAuth: {token.get('error_description', token)}")
            st.query_params.clear()
    except Exception as e:
        st.error(f"Error OAuth: {e}")
        st.query_params.clear()

# --- Configuración de la página ---
st.set_page_config(
    page_title = "LeadBot Colombia",
    page_icon = "🗺️",
    layout = "wide"
)

# --- Estilos CSS personalizados ---
st.markdown("""
    <style>
    html, body, [class*="css"] {
        font-family: 'Courier New', monospace;
    }
    h1 {
        color: #00D4AA;
        font-size: 2.5rem;
        font-weight: 800;
        letter-spacing: 2px;
    }
    h2, h3 {
        color: #00D4AA;
        letter-spacing: 1px;
    }
    [data-testid="metric-container"] {
        background-color: #1A1F2E;
        border: 1px solid #00D4AA;
        border-radius: 10px;
        padding: 15px;
    }
    .stButton > button {
        background-color: #00D4AA;
        color: #0E1117;
        font-weight: 700;
        border-radius: 8px;
        border: none;
        padding: 10px 20px;
        letter-spacing: 1px;
        transition: 0.3s;
    }
    .stButton > button:hover {
        background-color: #00F5C4;
        transform: translateY(-2px);
    }
    [data-testid="stSidebar"] {
        background-color: #1A1F2E;
        border-right: 1px solid #00D4AA33;
    }
    </style>
""", unsafe_allow_html=True)

# --- Título ---
st.markdown("""
    <div style='text-align: center; padding: 20px 0;'>
        <h1>🔍 LeadBot Colombia</h1>
        <p style='color: #00D4AA; font-size: 1.1rem; letter-spacing: 2px;'>
            ENCUENTRA · ANALIZA · EXPORTA
        </p>
        <p style='color: #888; font-size: 0.9rem;'>
            Leads B2B colombianos en segundos
        </p>
    </div>
    <hr style='border-color: #00D4AA33; margin-bottom: 30px;'>
""", unsafe_allow_html=True)

# --- Sidebar: Búsqueda ---
st.sidebar.header("🔍 Buscar Leads")
if "ultimo_query" not in st.session_state:
    st.session_state.ultimo_query = ""

query = st.sidebar.text_input(
    "Sector + Ciudad",
    placeholder = "Agencias Marketing Bogotá",
    key = "query_input"
)

buscar = st.sidebar.button("Buscar Leads")
if query and query != st.session_state.ultimo_query:
    buscar = True

if buscar and query:
    st.session_state.ultimo_query = query

# --- Filtros ---
st.sidebar.header("📊 Cantidad")
max_leads = st.sidebar.select_slider(
    "Leads por búsqueda",
    options=[20,40,60],
    value = 20
)

st.sidebar.header("🎯 Filtros")
min_rating = st.sidebar.slider("Rating mínimo", 0.0, 5.0, 0.0, 0.5)
min_resenas = st.sidebar.number_input("Reseñas mínimas:", min_value=0, value=0, step=10)

# --- Sidebar: Desconectar Google ---
if credenciales_validas():
    st.sidebar.divider()
    if st.sidebar.button("🔌 Desconectar cuenta de Google"):
        del st.session_state.google_token
        if os.path.exists("config/user_token.json"):
            os.remove("config/user_token.json")
        st.rerun()

# --- Lógica Principal ---
if "df" not in st.session_state:
    st.session_state.df = None

if buscar and not query:
    st.sidebar.warning("⚠️ Ingresa un sector y una ciudad")

if buscar and query:
    try:
        with st.spinner("Buscando..."):
            resultado = search_businesses(query, max_leads=max_leads)
            if not resultado:
                st.info("🔍 No se encontraron empresas. Prueba con otra búsqueda.")
            else:
                st.session_state.df = limpiar_datos(resultado)
    except ValueError as e:
        st.error(f"⚠️ Error: {e}")
    except ConnectionError:
        st.error("🔌 Problema de conexión. Revisa tu red e inténtalo de nuevo")
    except Exception as e:
        st.error(f"❌ Error inesperado: {e}")

# --- Mostrar resultados ---
if st.session_state.df is not None:
    df = st.session_state.df
    query = st.session_state.ultimo_query

    df = df[df["Rating"] >= min_rating]
    df = df[df["Reseñas_totales"] >= min_resenas]

    if df.empty:
        st.warning("⚠️ Ninguna empresa coincide con los filtros seleccionados.")
        st.stop()

    # --- Métricas ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Leads", len(df))
    col2.metric("Rating promedio", round(df["Rating"].mean(), 2))
    col3.metric("Con reseñas", len(df[df["Reseñas_totales"] > 0]))

    # --- Tabla ---
    st.subheader("📋 Resultados")
    st.dataframe(df, width="stretch")

    # --- Gráficos --- 1 Top 10 reseñas
    st.subheader("📊 Análisis visual")
    top_resenas = df.nlargest(10, "Reseñas_totales")
    fig1 = px.bar(
        top_resenas,
        x = "Reseñas_totales",
        y = "Nombre",
        orientation = "h",
        title = "🏆 Top 10 empresas por reseñas",
        color = "Reseñas_totales",
        color_continuous_scale = "teal",
        labels = {"Reseñas_totales": "Reseñas", "Nombre": "Empresa"}
    )
    fig1.update_layout(
        template = "plotly_dark",
        showlegend = False,
        yaxis = {"categoryorder": "total ascending"}
    )
    st.plotly_chart(fig1, use_container_width=True)

    # Gráfico 2: Top 10 por Rating
    top_rating = df.nlargest(10, "Rating")
    fig2 = px.bar(
        top_rating,
        x = "Rating",
        y = "Nombre",
        orientation = "h",
        title = "⭐ Top 10 empresas por rating",
        color = "Rating",
        color_continuous_scale = "teal",
        labels = {"Rating": "Rating", "Nombre": "Empresa"}
    )
    fig2.update_layout(
        template = "plotly_dark",
        showlegend = False,
        yaxis = {"categoryorder": "total ascending"},
        xaxis = {"range": [0,5]}
    )
    st.plotly_chart(fig2, use_container_width=True)

    # --- Gráfico 3: % empresas con web ---
    con_web = len(df[df["Sitio Web"] != "N/A"])
    sin_web = len(df[df["Sitio Web"] == "N/A"])
    fig3 = go.Figure(data=[go.Pie(
        labels=["Con sitio web", "Sin sitio web"],
        values = [con_web, sin_web],
        hole = 0.4,
        marker_colors = ["#00D4AA", "#1A1F2E"]
    )])
    fig3.update_layout(
        template = "plotly_dark",
        title = "🌐 Presencia Online"
    )
    st.plotly_chart(fig3, use_container_width=True)


    # --- Exportación ---
    st.subheader("📥 Exporta los resultados")

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="💾 Descargar CSV",
        data=csv,
        file_name=f"leads_{query.replace(' ', '_')}.csv",
        mime="text/csv"
    )

    # --- Google Sheets export ---
    if credenciales_validas():
        st.success("✅ Cuenta de Google conectada")
        if st.session_state.get("auto_export"):
            st.session_state.auto_export = False
            with st.spinner("Exportando..."):
                enlace = exportar_google_sheets(df, query, st.session_state.google_token)
            st.success("✅ ¡Leads cargados en un nuevo Google Sheet!")
            st.markdown(f"[Abrir la hoja]({enlace})")
        elif st.button("📊 Exportar a Google Sheets"):
            with st.spinner("Exportando..."):
                enlace = exportar_google_sheets(df, query, st.session_state.google_token)
            st.success("✅ ¡Leads cargados en un nuevo Google Sheet!")
            st.markdown(f"[Abrir la hoja]({enlace})")
    else:
        if st.button("📊 Exportar a Google Sheets"):
            st.session_state.mostrar_boton_oauth = True

        if st.session_state.get("mostrar_boton_oauth"):
            st.info("Para exportar, primero conecta tu cuenta de Google.")
            if st.button("🔗 Conecta tu cuenta de Google"):
                state_id = str(uuid.uuid4())
                with open(f"/tmp/oauth_state_{state_id}.pkl", "wb") as f:
                    pickle.dump({"df": df, "query": query}, f)
                oauth_url = construir_url_oauth(state=state_id)
                st.markdown(f"[🔗 Acceder con Google]({oauth_url})")
