# 🤖 LeadBot Colombia

> Encuentra, analiza y exporta leads B2B colombianos en segundos.

![Python](https://img.shields.io/badge/Python-3.13-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.x-red)
![Outscraper](https://img.shields.io/badge/Outscraper-API-green)

## 🎯 ¿Qué es LeadBot Colombia?

LeadBot Colombia es una herramienta de generación automática de leads B2B
para el mercado colombiano. Ingresa un sector y una ciudad — LeadBot
encuentra las empresas, las analiza y las exporta a CSV o Google Sheets.

**Ideal para:**

- Agencias de marketing que buscan nuevos clientes
- Consultores B2B que hacen prospecting
- Equipos comerciales que quieren automatizar la búsqueda

---

## ⚡ Funcionalidades

- 🔍 Búsqueda de empresas por sector y ciudad en toda Colombia
- 📧 Enriquecimiento automático con emails de contacto
- 📊 Análisis automático: rating, reseñas, presencia online
- 🎯 Filtros interactivos por rating mínimo y reseñas
- 💾 Exportación a CSV
- 📋 Exportación directa a Google Sheets
- 🌙 Interfaz dark mode profesional

---

## 🛠️ Stack Técnico

| Tecnología        | Uso                            |
| ----------------- | ------------------------------ |
| Python 3.13       | Lenguaje principal             |
| Streamlit         | Interfaz web                   |
| Pandas            | Limpieza y análisis de datos   |
| Outscraper API    | Extracción de datos (Google Maps) |
| Google Sheets API | Exportación a la nube          |
| gspread           | Integración con Google Sheets  |
| python-dotenv     | Gestión de variables de entorno |

---

## 🏗️ Arquitectura

```
leadbot-colombia/
│
├── app.py                  # Entry point — Streamlit UI
├── config/
│   └── settings.py         # Configuración global
├── src/
│   ├── scraper.py          # Extracción de datos (Outscraper, región CO)
│   ├── cleaner.py          # Limpieza de datos con Pandas
│   ├── exporter.py         # Export CSV y Google Sheets
│   └── auth.py             # Flujo OAuth de Google
├── data/
│   └── processed/          # Datos exportados
└── requirements.txt
```

---

## 🚀 Instalación

**1. Clona el repositorio**

```bash
git clone https://github.com/mrestebanmr/leadbot-colombia.git
cd leadbot-colombia
```

**2. Crea y activa el entorno virtual**

```bash
python3 -m venv venv
source venv/bin/activate
```

**3. Instala las dependencias**

```bash
pip install -r requirements.txt
```

**4. Configura las variables de entorno**

```bash
cp .env.example .env
```

Coloca tu API key de Outscraper, tu API key de Google Maps y el ID del Google Sheet en el archivo `.env`.

**5. Inicia la aplicación**

```bash
streamlit run app.py
```

---

## 🔐 Variables de entorno

Crea un archivo `.env` en la raíz del proyecto:

```
GOOGLE_MAPS_API_KEY=tu_google_maps_api_key_aqui
GOOGLE_SHEET_ID=tu_google_sheet_id_aqui
OUTSCRAPER_API_KEY=tu_outscraper_api_key_aqui
```

Para la exportación a Google Sheets necesitas además las credenciales OAuth en
`config/oauth_credentials.json` (descargadas desde Google Cloud Console).

---

## ☁️ Despliegue en Streamlit Cloud

1. **Sube el repo a GitHub** (los archivos sensibles ya están en `.gitignore`).
2. En [share.streamlit.io](https://share.streamlit.io) crea una nueva app apuntando a este repo, branch `main`, archivo `app.py`.
3. En **Settings → Secrets**, pega el contenido de [`.streamlit/secrets.toml.example`](.streamlit/secrets.toml.example) con tus valores reales:
   - `OUTSCRAPER_API_KEY` — **debe tener créditos disponibles** (si no, las búsquedas fallan con error 401).
   - `GOOGLE_MAPS_API_KEY`, `GOOGLE_SHEET_ID`.
   - Sección `[oauth_credentials]` (solo si quieres exportar a Google Sheets): `client_id`, `client_secret` y `redirect_uri`.
4. **OAuth en producción:** en [Google Cloud Console](https://console.cloud.google.com/apis/credentials) agrega la URL pública de tu app (ej. `https://tu-app.streamlit.app`) como **URI de redireccionamiento autorizado**, y pon esa misma URL en `redirect_uri` de los secrets.

> ⚠️ La exportación CSV funciona sin OAuth. Google Sheets requiere la sección `[oauth_credentials]`.

---

## 👨‍💻 Autor

**Esteban Muriel**
Python Developer & Data Science Student
🔗 [LinkedIn](https://www.linkedin.com/in/esteban-muriel-648b552ba/)
🐙 [GitHub](https://github.com/mrestebanmr)

---

## 📄 Licencia

MIT License — libre de usar, modificar y distribuir.
