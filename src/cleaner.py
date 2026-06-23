import pandas as pd

def limpiar_datos(empresas):
    df = pd.DataFrame(empresas)
    df = df.fillna("N/A")

    # Eliminar duplicados
    df = df.drop_duplicates(subset=["Nombre"])

    # Convierte a númerico - cualquier valor no convertible se vuelve NaN
    df["Rating"] = pd.to_numeric(df["Rating"], errors="coerce").fillna(0)
    df["Reseñas_totales"] = pd.to_numeric(df["Reseñas_totales"], errors="coerce").fillna(0)

    # Convertir tipos
    df["Rating"] = df["Rating"].astype(float)
    df["Reseñas_totales"] = df["Reseñas_totales"].astype(int)

    # Ordenar por rating descendente
    df = df.sort_values("Rating", ascending=False).reset_index(drop=True)

    return df
