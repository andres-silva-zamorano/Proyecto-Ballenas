import polars as pl
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import sys

# --- CONFIGURACIÓN ---
# Apuntamos al archivo que realmente genera el monitor
FILE_PATH = os.path.join("data", "raw", "sesion_ballenas.csv")

def cargar_datos():
    if not os.path.exists(FILE_PATH):
        print(f"ERROR: No se encuentra el archivo en: {FILE_PATH}")
        print("Asegúrate de haber ejecutado 'main_monitor_v1.py' por un par de minutos.")
        sys.exit(1)

    print(f"Cargando datos desde: {FILE_PATH}...")
    
    try:
        # Cargar con Polars
        df = pl.read_csv(FILE_PATH)
        
        if df.height == 0:
            print("El archivo CSV está vacío.")
            sys.exit(0)

        # Manejo inteligente de la Fecha/Hora
        # El monitor guarda una columna 'Timestamp' (string) y 'timestamp' (posiblemente de indicadores)
        # Vamos a intentar parsear la columna de texto que es más legible
        # Corrección robusta de Timestamp
        if "Timestamp" in df.columns:
            # Caso 1: Timestamp es número (Unix Epoch en segundos o ms)
            if df["Timestamp"].dtype in [pl.Int64, pl.Int32, pl.Float64]:
                # Si el número es muy grande (> 10^11), asumimos milisegundos
                es_ms = df["Timestamp"].mean() > 10000000000
                unit = "ms" if es_ms else "s"
                
                df = df.with_columns(
                    pl.from_epoch(pl.col("Timestamp"), time_unit=unit).alias("datetime")
                )
            # Caso 2: Timestamp es String ("2025-...")
            else:
                try:
                    df = df.with_columns(
                        pl.col("Timestamp").str.to_datetime(strict=False).alias("datetime")
                    )
                except:
                    df = df.with_columns(pl.int_range(0, df.height).alias("datetime"))
        else:
            df = df.with_columns(pl.int_range(0, df.height).alias("datetime"))

        return df
        
    except Exception as e:
        print(f"Error leyendo el CSV: {e}")
        sys.exit(1)

def generar_grafico(df):
    print(f"Generando gráfico con {df.height} registros...")
    
    # Crear figura con 2 paneles
    fig = make_subplots(
        rows=2, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.05,
        row_heights=[0.7, 0.3], # 70% Precio, 30% Ballenas
        subplot_titles=("BTCUSD | Precio vs EMA", "Actividad Ballenas (Micro Score)")
    )

    # --- PANEL 1: PRECIO ---
    fig.add_trace(go.Scatter(
        x=df["datetime"], 
        y=df["Close_Price"],
        mode='lines',
        name='Precio',
        line=dict(color='#00F0FF', width=2)
    ), row=1, col=1)

    # EMA Principal
    if "EMA_Princ" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["datetime"], 
            y=df["EMA_Princ"],
            mode='lines',
            name='EMA Trend',
            line=dict(color='#FFD700', width=1, dash='dot')
        ), row=1, col=1)

    # --- PANEL 2: BALLENAS (Micro Score) ---
    # Usamos las columnas extra que agregamos al final
    if "Micro_Score" in df.columns:
        scores = df["Micro_Score"].to_list()
        # Colores: Verde si es positivo, Rojo si es negativo
        colors = ['#00FF00' if x >= 0 else '#FF0000' for x in scores]
        
        fig.add_trace(go.Bar(
            x=df["datetime"],
            y=df["Micro_Score"],
            marker_color=colors,
            name='Presión Neta'
        ), row=2, col=1)

        # Líneas de Referencia (Umbrales de Ballena)
        fig.add_hline(y=0.25, line_dash="dash", line_color="green", opacity=0.5, row=2, col=1)
        fig.add_hline(y=-0.25, line_dash="dash", line_color="red", opacity=0.5, row=2, col=1)

    # --- DISEÑO ---
    fig.update_layout(
        template="plotly_dark",
        title_text="Auditoría de Sesión - Proyecto Ballenas",
        hovermode="x unified",
        height=800
    )
    
    # Eje Y del score fijo para ver la magnitud real (-1 a 1)
    fig.update_yaxes(range=[-1.1, 1.1], title="Presión (-1 a 1)", row=2, col=1)

    # Guardar
    output_file = "reporte_sesion.html"
    fig.write_html(output_file)
    print(f"\n[EXITO] Reporte generado: {output_file}")
    
    # Abrir automáticamente
    if os.name == 'nt': # Solo Windows
        os.system(f"start {output_file}")

if __name__ == "__main__":
    datos = cargar_datos()
    generar_grafico(datos)