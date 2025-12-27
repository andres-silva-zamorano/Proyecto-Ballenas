import polars as pl
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import sys

# --- CONFIGURACIÓN ---
FILE_PATH = os.path.join("data", "raw", "sesion_ballenas.csv")

# Mapa de colores para los regímenes
REGIMEN_COLORS = {
    0: "gray",    # Lateral
    1: "#90EE90", # Alcista Débil (Verde claro)
    2: "#FFCCCC", # Bajista Débil (Rojo claro)
    3: "#00FF00", # Alcista Volátil (Verde)
    4: "#FF0000", # Bajista Volátil (Rojo)
    5: "#006400", # TENDENCIA ALCISTA FUERTE (Verde Oscuro)
    6: "#8B0000"  # TENDENCIA BAJISTA FUERTE (Rojo Oscuro)
}

def cargar_datos():
    if not os.path.exists(FILE_PATH):
        print(f"ERROR: No existe {FILE_PATH}")
        sys.exit(1)

    try:
        # Intentamos leer. Si falla por bloqueo de archivo (Monitor escribiendo), avisamos.
        df = pl.read_csv(FILE_PATH, ignore_errors=True)
        
        # Parseo de Fechas (Compatible con tu Logger actual)
        if "Timestamp" in df.columns:
            try:
                df = df.with_columns(
                    pl.col("Timestamp").str.to_datetime(strict=False).alias("datetime")
                )
            except:
                # Fallback si falla el parseo
                df = df.with_columns(pl.int_range(0, df.height).alias("datetime"))
        else:
            df = df.with_columns(pl.int_range(0, df.height).alias("datetime"))

        return df
    except Exception as e:
        print(f"Error: {e}")
        print("TIP: Si el monitor está corriendo, a veces bloquea el archivo. Copia el CSV a otro nombre e intenta leer la copia.")
        sys.exit(1)

def generar_reporte(df):
    print(f"Generando reporte IA con {df.height} velas...")

    # Creamos 3 Filas: Precio, Ballenas, Cerebro IA
    fig = make_subplots(
        rows=3, cols=1, 
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.5, 0.25, 0.25],
        subplot_titles=("Precio vs EMA", "Actividad Ballenas (Micro)", "Cerebro IA (Régimen Detectado)")
    )

    # --- PANEL 1: PRECIO ---
    fig.add_trace(go.Scatter(x=df["datetime"], y=df["Close_Price"], mode='lines', name='Precio', line=dict(color='#00F0FF')), row=1, col=1)
    if "EMA_Princ" in df.columns:
        fig.add_trace(go.Scatter(x=df["datetime"], y=df["EMA_Princ"], mode='lines', name='EMA', line=dict(color='yellow', dash='dot')), row=1, col=1)

    # --- PANEL 2: BALLENAS ---
    if "Micro_Score" in df.columns:
        cols = ['#00FF00' if x >= 0 else '#FF0000' for x in df["Micro_Score"].to_list()]
        fig.add_trace(go.Bar(x=df["datetime"], y=df["Micro_Score"], marker_color=cols, name='Flow Ballenas'), row=2, col=1)
        fig.add_hline(y=0.25, line_dash="dot", row=2, col=1)
        fig.add_hline(y=-0.25, line_dash="dot", row=2, col=1)

    # --- PANEL 3: INTELIGENCIA ARTIFICIAL ---
    if "Regimen_Actual" in df.columns:
        # Truco visual: Scatter plot escalonado
        regimenes = df["Regimen_Actual"].to_list()
        colors_reg = [REGIMEN_COLORS.get(r, "white") for r in regimenes]
        
        fig.add_trace(go.Scatter(
            x=df["datetime"], 
            y=df["Regimen_Actual"],
            mode='markers+lines',
            line=dict(shape='hv', width=1, color='gray'), # Línea escalonada gris tenue
            marker=dict(size=6, color=colors_reg), # Puntos de color según régimen
            name='Régimen IA'
        ), row=3, col=1)
    else:
        print("AVISO: No se encontraron datos de IA (Regimen_Actual) en el CSV.")

    # Ajustes Finales
    fig.update_layout(template="plotly_dark", height=900, title_text=f"Auditoría Completa IA - {FILE_PATH}")
    fig.update_yaxes(range=[-1.1, 1.1], row=2, col=1) # Rango fijo ballenas
    fig.update_yaxes(range=[-0.5, 6.5], row=3, col=1, tickvals=[0,1,2,3,4,5,6], title="Régimen (0-6)")

    fig.write_html("reporte_ia_full.html")
    print("Abriendo reporte...")
    if os.name == 'nt': os.system("start reporte_ia_full.html")

if __name__ == "__main__":
    df = cargar_datos()
    generar_reporte(df)