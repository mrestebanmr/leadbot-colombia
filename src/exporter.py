import json
from datetime import datetime
import gspread
from google.oauth2.credentials import Credentials as OAuthCredentials

def exportar_google_sheets(df, query, credenciales_dict):
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file"
    ]

    with open("config/oauth_credentials.json") as f:
        oauth_config = json.load(f)["web"]
    credenciales = OAuthCredentials(
        token=credenciales_dict["access_token"],
        refresh_token=credenciales_dict.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=oauth_config["client_id"],
        client_secret=oauth_config["client_secret"],
        scopes=scopes,
    )

    # Conecta con Google Sheets
    cliente = gspread.authorize(credenciales)

    # Crea un nuevo Sheet con nombre basado en la query y fecha
    timestamp = datetime.now().strftime("%Y-%m-%d")
    nombre_hoja = f"LeadBot – {query} – {timestamp}"
    hoja = cliente.create(nombre_hoja)
    worksheet = hoja.get_worksheet(0)

    # Añade columnas de metadata
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    sheet_id = hoja.id
    df = df.copy()
    df.insert(0, "Fecha búsqueda", timestamp)
    df.insert(1, "Búsqueda", query)

    # Escribe encabezados y datos
    worksheet.append_row(df.columns.tolist())
    datos = df.astype(str).values.tolist()
    for fila in datos:
        fila_limpia = [str(v) if not isinstance(v, (str, int, float)) else v for v in fila]
        worksheet.append_row(fila_limpia)

    return f"https://docs.google.com/spreadsheets/d/{sheet_id}"
