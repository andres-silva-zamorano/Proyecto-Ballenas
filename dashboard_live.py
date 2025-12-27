import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import polars as pl
import os

# --- CONFIGURACIÓN ---
FILE_PATH = os.path.join("data", "raw", "live_lite.csv")
UPDATE_INTERVAL_MS = 1000  # 1 segundo

# Colores IA
REGIMEN_COLORS = {
    0: "gray",    1: "#90EE90", 2: "#FFCCCC",
    3: "#00FF00", 4: "#FF0000", 5: "#006400", 6: "#8B0000"
}

app = dash.Dash(__name__)
app.title = "Monitor Táctico (Live)"

app.layout = html.Div(style={'backgroundColor': '#111111', 'color': '#00F0FF', 'height': '100vh', 'padding': '0'}, children=[
    html.H2("MONITOR TÁCTICO | 1S", style={'textAlign': 'center', 'paddingTop': '10px', 'fontSize': '18px'}),
    dcc.Graph(id='live-graph', style={'height': '90vh'}),
    dcc.Interval(id='interval-live', interval=UPDATE_INTERVAL_MS, n_intervals=0)
])

@app.callback(Output('live-graph', 'figure'),
              [Input('interval-live', 'n_intervals')])
def update_live(n):
    # 1. Verificación de Archivo
    if not os.path.exists(FILE_PATH):
        # Retorna un gráfico vacío con mensaje de espera
        return {
            "layout": {
                "xaxis": {"visible": False}, "yaxis": {"visible": False},
                "annotations": [{"text": "ESPERANDO CREACIÓN DE ARCHIVO...", "xref": "paper", "yref": "paper", "showarrow": False, "font": {"color": "red", "size": 20}}]
            }
        }

    try:
        # 2. Lectura Forzada de Tipos (Esto soluciona el gráfico vacío)
        # Le decimos explícitamente qué es cada columna para que no se confunda
        df = pl.read_csv(
            FILE_PATH, 
            ignore_errors=True,
            schema_overrides={
                "Timestamp": pl.Int64,       # Importante: Entero para milisegundos
                "Close_Price": pl.Float64,
                "EMA_Princ": pl.Float64,
                "Micro_Score": pl.Float64,
                "Regimen_Actual": pl.Int64
            }
        )
        
        # Si está vacío, esperar
        if df.height < 1:
            return dash.no_update

        print(f"[DEBUG] Leyendo {df.height} filas para el Live...")

        # 3. Conversión de Fecha (Maneja Int o String)
        if df["Timestamp"].dtype == pl.Int64:
            # Caso ideal: viene del live_lite como milisegundos
            df = df.with_columns(pl.from_epoch("Timestamp", time_unit="ms").alias("datetime"))
        else:
            # Fallback por si acaso
            df = df.with_columns(pl.int_range(0, df.height).alias("datetime"))

        # Recorte visual (últimos 100 puntos para zoom táctico)
        if df.height > 100:
            df = df.tail(100)

    except Exception as e:
        print(f"[ERROR DASH] {e}")
        return dash.no_update

    # 4. Construcción Gráfica
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.02,
        row_heights=[0.5, 0.25, 0.25],
        subplot_titles=("Precio", "Ballenas", "IA")
    )

    # Panel 1: Precio
    fig.add_trace(go.Scatter(x=df["datetime"], y=df["Close_Price"], mode='lines', name='Precio', line=dict(color='#00F0FF', width=1.5)), row=1, col=1)
    if "EMA_Princ" in df.columns:
        fig.add_trace(go.Scatter(x=df["datetime"], y=df["EMA_Princ"], mode='lines', name='EMA', line=dict(color='#FFD700', dash='dot')), row=1, col=1)

    # Panel 2: Ballenas
    if "Micro_Score" in df.columns:
        vals = df["Micro_Score"].to_list()
        cols = ['#00FF00' if x >= 0 else '#FF0000' for x in vals]
        fig.add_trace(go.Bar(x=df["datetime"], y=df["Micro_Score"], marker_color=cols, name='Flow'), row=2, col=1)

    # Panel 3: IA
    if "Regimen_Actual" in df.columns:
        regimenes = df["Regimen_Actual"].to_list()
        colors_reg = [REGIMEN_COLORS.get(r, "white") for r in regimenes]
        fig.add_trace(go.Scatter(
            x=df["datetime"], y=df["Regimen_Actual"], mode='markers+lines',
            line=dict(shape='hv', width=1, color='gray'),
            marker=dict(size=6, color=colors_reg), name='IA'
        ), row=3, col=1)

    fig.update_layout(
        template="plotly_dark", 
        margin=dict(l=10, r=10, t=30, b=10), 
        uirevision='constant', 
        hovermode="x unified",
        paper_bgcolor="#111111",
        plot_bgcolor="#111111"
    )
    
    fig.update_yaxes(gridcolor="#222", row=1, col=1)
    fig.update_yaxes(range=[-1.1, 1.1], gridcolor="#222", row=2, col=1)
    fig.update_yaxes(range=[-0.5, 6.5], tickvals=[0,1,2,3,4,5,6], gridcolor="#222", row=3, col=1)

    return fig

if __name__ == '__main__':
    print("Iniciando Dashboard Live en puerto 8050...")
    app.run(debug=False, port=8050)