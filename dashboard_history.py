import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import polars as pl
import os

# --- CONFIGURACIÓN ---
FILE_PATH = os.path.join("data", "raw", "sesion_ballenas.csv")
UPDATE_INTERVAL_MS = 60 * 1000  # 1 minuto
HISTORY_CANDLES = 2880 # 48 Horas

# Mapa de Colores
REGIMEN_COLORS = {
    0: "gray",    1: "#90EE90", 2: "#FFCCCC",
    3: "#00FF00", 4: "#FF0000", 5: "#006400", 6: "#8B0000"
}

app = dash.Dash(__name__)
app.title = "Histórico Ballenas IA (48h)"

app.layout = html.Div(style={'backgroundColor': '#000000', 'color': '#00F0FF', 'height': '100vh', 'padding': '0'}, children=[
    html.H2("PANEL MACRO: HISTORIA RECIENTE (48H)", style={'textAlign': 'center', 'paddingTop': '10px', 'color': '#FFD700'}),
    dcc.Graph(id='history-graph', style={'height': '90vh'}),
    dcc.Interval(id='interval-history', interval=UPDATE_INTERVAL_MS, n_intervals=0)
])

@app.callback(Output('history-graph', 'figure'),
              [Input('interval-history', 'n_intervals')])
def update_history(n):
    try:
        if not os.path.exists(FILE_PATH):
            return dash.no_update
            
        df = pl.read_csv(FILE_PATH, ignore_errors=True)
        
        # 1. Parseo de Fechas
        if "Timestamp" in df.columns:
            try:
                df = df.with_columns(pl.col("Timestamp").str.to_datetime(strict=False).alias("datetime"))
            except:
                df = df.with_columns(pl.int_range(0, df.height).alias("datetime"))
        else:
            df = df.with_columns(pl.int_range(0, df.height).alias("datetime"))

        # 2. Asegurar que Micro_Score sea numérico (evitar errores de texto)
        if "Micro_Score" in df.columns:
            df = df.with_columns(pl.col("Micro_Score").cast(pl.Float64, strict=False).fill_null(0.0))

        # 3. Filtro de historial
        if df.height > HISTORY_CANDLES:
            df = df.tail(HISTORY_CANDLES)
            
    except Exception:
        return dash.no_update

    # CONSTRUCCIÓN DEL GRÁFICO
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05,
        row_heights=[0.6, 0.20, 0.20],
        subplot_titles=("Acción de Precio", "Presión Ballenas (Sin Bordes)", "Régimen IA")
    )

    # PANEL 1: PRECIO
    fig.add_trace(go.Scatter(
        x=df["datetime"], y=df["Close_Price"], 
        mode='lines', name='Precio', line=dict(color='#00F0FF', width=1.2)
    ), row=1, col=1)

    if "EMA_Princ" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["datetime"], y=df["EMA_Princ"], 
            mode='lines', name='EMA Trend', line=dict(color='#FFD700', dash='dot', width=1)
        ), row=1, col=1)

    # PANEL 2: BALLENAS (CORREGIDO: Colores Neón + Sin Bordes)
    if "Micro_Score" in df.columns:
        vals = df["Micro_Score"].to_list()
        # Colores más brillantes (LimeGreen y Red)
        colores = ['#00FF00' if x >= 0 else '#FF0040' for x in vals]
        
        fig.add_trace(go.Bar(
            x=df["datetime"], 
            y=df["Micro_Score"], 
            marker=dict(
                color=colores,
                line=dict(width=0) # <--- LA CLAVE: Borde cero para que no se vea negro
            ),
            name='Presión'
        ), row=2, col=1)

    # PANEL 3: IA
    if "Regimen_Actual" in df.columns:
        regimenes = df["Regimen_Actual"].to_list()
        colors_reg = [REGIMEN_COLORS.get(r, "white") for r in regimenes]
        
        fig.add_trace(go.Scatter(
            x=df["datetime"], y=df["Regimen_Actual"], 
            mode='markers',
            marker=dict(size=3, color=colors_reg, symbol='square'), # Puntos más pequeños para ver densidad
            name='IA'
        ), row=3, col=1)

    # ESTÉTICA
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#000000", 
        plot_bgcolor="#000000",
        hovermode="x unified",
        uirevision='constant',
        xaxis=dict(rangeslider=dict(visible=False), type="date")
    )
    
    # Escalas fijas
    fig.update_yaxes(gridcolor="#222", row=1, col=1)
    fig.update_yaxes(range=[-1.0, 1.0], gridcolor="#222", row=2, col=1) 
    fig.update_yaxes(range=[-0.5, 6.5], tickvals=[0,1,2,3,4,5,6], gridcolor="#222", row=3, col=1)

    return fig

if __name__ == '__main__':
    app.run(debug=False, port=8051)