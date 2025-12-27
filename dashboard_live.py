import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import polars as pl
import os

# --- CONFIGURACIÓN ---
FILE_PATH = os.path.join("data", "raw", "sesion_ballenas.csv")
UPDATE_INTERVAL_MS = 1000  # Actualizar cada 1000ms (1 segundo)

# Mapa de Colores de Regímenes (Mismo de antes)
REGIMEN_COLORS = {
    0: "gray",    1: "#90EE90", 2: "#FFCCCC",
    3: "#00FF00", 4: "#FF0000", 5: "#006400", 6: "#8B0000"
}

# Inicializar la App de Dash
app = dash.Dash(__name__)
app.title = "Monitor Ballenas IA"

# --- LAYOUT (La estructura de la página web) ---
app.layout = html.Div(style={'backgroundColor': '#111111', 'color': '#00F0FF', 'height': '100vh', 'padding': '0'}, children=[
    html.H2("MONITOR INSTITUCIONAL EN VIVO | BTCUSD", style={'textAlign': 'center', 'paddingTop': '20px'}),
    
    # El Gráfico
    dcc.Graph(id='live-graph', style={'height': '85vh'}),
    
    # El "Corazón" que late cada 1 segundo para pedir datos
    dcc.Interval(
        id='interval-component',
        interval=UPDATE_INTERVAL_MS, 
        n_intervals=0
    )
])

# --- LÓGICA DE ACTUALIZACIÓN ---
@app.callback(Output('live-graph', 'figure'),
              [Input('interval-component', 'n_intervals')])
def update_graph_live(n):
    # 1. Leer CSV de forma segura (si el monitor está escribiendo, puede fallar, así que usamos try)
    try:
        if not os.path.exists(FILE_PATH):
            return dash.no_update
            
        df = pl.read_csv(FILE_PATH, ignore_errors=True)
        
        if df.height < 5: # Esperar a tener algo de datos
            return dash.no_update

        # Parseo de Fechas
        if "Timestamp" in df.columns:
            try:
                df = df.with_columns(pl.col("Timestamp").str.to_datetime(strict=False).alias("datetime"))
            except:
                df = df.with_columns(pl.int_range(0, df.height).alias("datetime"))
        else:
            df = df.with_columns(pl.int_range(0, df.height).alias("datetime"))

        # Recortar para rendimiento: Mostrar solo las últimas 500 velas si hay muchas
        if df.height > 500:
            df = df.tail(500)

    except Exception as e:
        # Si falla la lectura, no actualizamos nada y esperamos al siguiente segundo
        return dash.no_update

    # 2. Construir la Figura (Igual que antes)
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.02,
        row_heights=[0.5, 0.25, 0.25],
        subplot_titles=("Precio vs EMA", "Flow Ballenas (Micro)", "Régimen IA")
    )

    # Panel 1: Precio
    fig.add_trace(go.Scatter(x=df["datetime"], y=df["Close_Price"], mode='lines', name='Precio', 
                             line=dict(color='#00F0FF', width=1.5)), row=1, col=1)
    if "EMA_Princ" in df.columns:
        fig.add_trace(go.Scatter(x=df["datetime"], y=df["EMA_Princ"], mode='lines', name='EMA', 
                                 line=dict(color='#FFD700', dash='dot', width=1)), row=1, col=1)

    # Panel 2: Ballenas
    if "Micro_Score" in df.columns:
        colors = ['#00FF00' if x >= 0 else '#FF0000' for x in df["Micro_Score"].to_list()]
        fig.add_trace(go.Bar(x=df["datetime"], y=df["Micro_Score"], marker_color=colors, name='Flow'), row=2, col=1)
        fig.add_hline(y=0.25, line_dash="dot", line_color="green", row=2, col=1)
        fig.add_hline(y=-0.25, line_dash="dot", line_color="red", row=2, col=1)

    # Panel 3: IA
    if "Regimen_Actual" in df.columns:
        regimenes = df["Regimen_Actual"].to_list()
        colors_reg = [REGIMEN_COLORS.get(r, "white") for r in regimenes]
        fig.add_trace(go.Scatter(
            x=df["datetime"], y=df["Regimen_Actual"], mode='markers+lines',
            line=dict(shape='hv', width=1, color='gray'),
            marker=dict(size=5, color=colors_reg), name='IA'
        ), row=3, col=1)

    # ESTÉTICA FINAL
    fig.update_layout(
        template="plotly_dark",
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor="#111111",
        plot_bgcolor="#111111",
        hovermode="x unified",
        # UIREVISION: ¡MAGIA! Esto evita que el zoom se resetee cada vez que se actualiza
        uirevision='constant' 
    )
    
    fig.update_yaxes(gridcolor="#333333", row=1, col=1)
    fig.update_yaxes(range=[-1.1, 1.1], gridcolor="#333333", row=2, col=1)
    fig.update_yaxes(range=[-0.5, 6.5], tickvals=[0,1,2,3,4,5,6], gridcolor="#333333", row=3, col=1)
    fig.update_xaxes(gridcolor="#333333")

    return fig

if __name__ == '__main__':
    # Debug=False para evitar reinicios innecesarios en producción
    app.run_server(debug=False, port=8050)