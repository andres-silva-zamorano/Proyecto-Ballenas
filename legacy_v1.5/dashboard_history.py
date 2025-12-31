import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import polars as pl
import os
from datetime import datetime, timedelta

# --- CONFIGURACIÓN ---
FILE_PATH = os.path.join("data", "raw", "sesion_ballenas.csv")
UPDATE_INTERVAL_MS = 60 * 1000  # 1 minuto

REGIMEN_COLORS = {
    0: "gray",    1: "#90EE90", 2: "#FFCCCC",
    3: "#00FF00", 4: "#FF0000", 5: "#006400", 6: "#8B0000"
}

TIMEFRAME_OPTIONS = [
    {'label': '1 Minuto', 'value': '1m'},
    {'label': '5 Minutos', 'value': '5m'},
    {'label': '15 Minutos', 'value': '15m'},
    {'label': '1 Hora', 'value': '1h'},
]

HISTORY_OPTIONS = [
    {'label': '6 Horas', 'value': 6},
    {'label': '12 Horas', 'value': 12},
    {'label': '24 Horas', 'value': 24},
    {'label': 'Todo', 'value': 0},
]

app = dash.Dash(__name__)
app.title = "Histórico Estratégico V3.1"

app.layout = html.Div(style={'backgroundColor': '#000000', 'color': '#00F0FF', 'height': '100vh', 'padding': '10px'}, children=[
    
    # HEADER DE CONTROLES
    html.Div([
        html.H2("DETECTOR DE TRAMPAS", style={'color': '#FFD700', 'margin': '0', 'marginRight': '20px', 'fontSize': '20px'}),
        
        # Agrupación
        html.Div([
            html.Label("Agrupar:", style={'color': 'white', 'fontWeight': 'bold', 'marginRight': '5px'}),
            dcc.Dropdown(id='dropdown-timeframe', options=TIMEFRAME_OPTIONS, value='5m', clearable=False, style={'width': '120px', 'color': 'black'})
        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),

        # Ventana Historia
        html.Div([
            html.Label("Ver:", style={'color': 'white', 'fontWeight': 'bold', 'marginRight': '5px'}),
            dcc.Dropdown(id='dropdown-history', options=HISTORY_OPTIONS, value=24, clearable=False, style={'width': '120px', 'color': 'black'})
        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '25px'}),

        # NUEVO: SLIDER DE SENSIBILIDAD
        html.Div([
            html.Label("Sensibilidad del Radar:", style={'color': '#00F0FF', 'fontWeight': 'bold', 'marginBottom': '5px'}),
            dcc.Slider(
                id='slider-umbral',
                min=0.01, max=0.30, step=0.01,
                value=0.08, # VALOR POR DEFECTO MÁS BAJO (0.08)
                marks={0.01: 'Máx (Ruido)', 0.08: 'Normal', 0.15: 'Fuerte', 0.30: 'Extremo'},
                tooltip={"placement": "bottom", "always_visible": True}
            )
        ], style={'flex': '1', 'maxWidth': '400px'})

    ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '5px', 'borderBottom': '1px solid #333', 'paddingBottom': '10px'}),

    dcc.Graph(id='history-graph', style={'height': '85vh'}),
    dcc.Interval(id='interval-history', interval=UPDATE_INTERVAL_MS, n_intervals=0)
])

def procesar_logica_estrategia(df, timeframe_val, umbral):
    # Agrupación dinámica con Polars
    q = (
        df.sort("datetime")
        .group_by_dynamic("datetime", every=timeframe_val)
        .agg([
            pl.col("Close_Price").first().alias("open_seg"),
            pl.col("Close_Price").last().alias("close_seg"),
            pl.col("EMA_Princ").last().alias("ema_last"),
            pl.col("Micro_Score").mean().alias("score_avg"),
            pl.col("Regimen_Actual").mode().first().alias("regimen_mode")
        ])
    )
    df_agg = q
    
    # Delta de precio
    df_agg = df_agg.with_columns(
        (pl.col("close_seg") - pl.col("open_seg")).alias("price_delta")
    )

    # LÓGICA DE DETECCIÓN (Usando el umbral dinámico)
    # Absorción: Score muy negativo (< -umbral) PERO Precio >= 0
    # Distribución: Score muy positivo (> umbral) PERO Precio <= 0
    df_agg = df_agg.with_columns(
        pl.when((pl.col("score_avg") < -umbral) & (pl.col("price_delta") >= 0))
          .then(pl.lit("ABSORCION"))
          .when((pl.col("score_avg") > umbral) & (pl.col("price_delta") <= 0))
          .then(pl.lit("DISTRIBUCION"))
          .otherwise(pl.lit("NORMAL"))
          .alias("estrategia")
    )

    return df_agg

@app.callback(
    Output('history-graph', 'figure'),
    [Input('interval-history', 'n_intervals'),
     Input('dropdown-timeframe', 'value'),
     Input('dropdown-history', 'value'),
     Input('slider-umbral', 'value')] # <--- Nuevo Input
)
def update_history(n, timeframe_val, history_val, umbral_val):
    if not os.path.exists(FILE_PATH): return dash.no_update
    
    try:
        df = pl.read_csv(FILE_PATH, ignore_errors=True)
        cols_check = ["Close_Price", "EMA_Princ", "Micro_Score", "Regimen_Actual"]
        for c in cols_check:
            if c in df.columns: df = df.with_columns(pl.col(c).cast(pl.Float64, strict=False).fill_null(0))

        if "Timestamp" in df.columns:
            try: df = df.with_columns(pl.col("Timestamp").str.to_datetime(strict=False).alias("datetime"))
            except: return dash.no_update
        
        df = df.drop_nulls(subset=["datetime"]).sort("datetime")

        if history_val > 0:
            cutoff = datetime.now() - timedelta(hours=history_val)
            df = df.filter(pl.col("datetime") >= cutoff)
        
        if df.height == 0: return dash.no_update

        # --- PROCESAMIENTO ---
        if timeframe_val == '1m':
            # Lógica cruda para 1m
            df = df.with_columns([
                (pl.col("Close_Price") - pl.col("Close_Price").shift(1).fill_null(pl.col("Close_Price"))).alias("price_delta"),
                pl.col("Micro_Score").alias("score_avg"),
                pl.col("Close_Price").alias("close_seg"),
                pl.col("EMA_Princ").alias("ema_last"),
                pl.col("Regimen_Actual").alias("regimen_mode")
            ])
            # Usamos el umbral del slider
            df = df.with_columns(
                pl.when((pl.col("score_avg") < -umbral_val) & (pl.col("price_delta") >= 0)).then(pl.lit("ABSORCION"))
                  .when((pl.col("score_avg") > umbral_val) & (pl.col("price_delta") <= 0)).then(pl.lit("DISTRIBUCION"))
                  .otherwise(pl.lit("NORMAL")).alias("estrategia")
            )
        else:
            # Lógica agrupada pasando el umbral
            df = procesar_logica_estrategia(df, timeframe_val, umbral_val)

        # --- GRÁFICO ---
        fig = make_subplots(
            rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03,
            row_heights=[0.6, 0.20, 0.20],
            subplot_titles=("Precio + Trampas", "Presión Ballenas", "Régimen IA")
        )

        # Precio y EMA
        fig.add_trace(go.Scatter(x=df["datetime"], y=df["close_seg"], mode='lines', name='Precio', line=dict(color='#00F0FF', width=1.5)), row=1, col=1)
        if "ema_last" in df.columns:
            fig.add_trace(go.Scatter(x=df["datetime"], y=df["ema_last"], mode='lines', name='EMA', line=dict(color='#FFD700', dash='dot', width=1)), row=1, col=1)

        # TRIÁNGULOS DE ESTRATEGIA
        df_abs = df.filter(pl.col("estrategia") == "ABSORCION")
        if df_abs.height > 0:
            fig.add_trace(go.Scatter(
                x=df_abs["datetime"], y=df_abs["close_seg"],
                mode='markers', name='Absorción',
                marker=dict(symbol='triangle-up', size=14, color='cyan', line=dict(width=2, color='white'))
            ), row=1, col=1)

        df_dist = df.filter(pl.col("estrategia") == "DISTRIBUCION")
        if df_dist.height > 0:
            fig.add_trace(go.Scatter(
                x=df_dist["datetime"], y=df_dist["close_seg"],
                mode='markers', name='Distribución',
                marker=dict(symbol='triangle-down', size=14, color='magenta', line=dict(width=2, color='white'))
            ), row=1, col=1)

        # Barras Ballenas
        vals = df["score_avg"].to_list()
        cols = ['#00FF00' if x >= 0 else '#FF0040' for x in vals]
        fig.add_trace(go.Bar(x=df["datetime"], y=df["score_avg"], marker=dict(color=cols), name='Presión'), row=2, col=1)
        
        # Líneas de umbral dinámicas en el gráfico de ballenas para referencia visual
        fig.add_hline(y=umbral_val, line_dash="dot", line_color="gray", row=2, col=1)
        fig.add_hline(y=-umbral_val, line_dash="dot", line_color="gray", row=2, col=1)

        # Régimen IA
        regimenes = df["regimen_mode"].to_list()
        colors_reg = []
        for r in regimenes:
            try: colors_reg.append(REGIMEN_COLORS.get(int(r), "white"))
            except: colors_reg.append("white")
        fig.add_trace(go.Scatter(x=df["datetime"], y=df["regimen_mode"], mode='markers', marker=dict(size=5, color=colors_reg, symbol='square'), name='Régimen'), row=3, col=1)

        fig.update_layout(
            template="plotly_dark", paper_bgcolor="black", plot_bgcolor="black", 
            hovermode="x unified", uirevision='constant', margin=dict(l=10, r=10, t=10, b=10),
            legend=dict(orientation="h", y=1.01, x=0.5, xanchor="center")
        )
        fig.update_yaxes(gridcolor="#222")
        
        return fig

    except Exception as e:
        print(f"Error: {e}")
        return dash.no_update

if __name__ == '__main__':
    print(">>> DASHBOARD V3.1 AJUSTABLE (PUERTO 8051) <<<")
    app.run(debug=False, port=8051, host='0.0.0.0')