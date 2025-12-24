# app_review.py
import polars as pl
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import ListedColormap, BoundaryNorm
import numpy as np
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import data_loader
import indicators
import feature_engineering
import ai_logic
import config

def plot_review():
    print(f"\n--- 📊 Auditoría Histórica: {config.SYMBOL} ---")
    
    # --- CORRECCIÓN: INICIAR CONEXIÓN MT5 ---
    if not data_loader.initialize_mt5():
        print("❌ Error: No se pudo conectar a MetaTrader 5")
        return
    # ----------------------------------------

    # 1. Cargar el Modelo
    if ai_logic.load_model() is None:
        return

    # 2. Descargar Datos (Última semana)
    print("1. Descargando historial reciente...")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7) # 7 días atrás
    
    # Velas
    # Descargamos un buffer grande para asegurar que cubrimos la fecha
    df_c = data_loader.get_candles(config.SYMBOL, config.TIMEFRAME, n_candles=15000)
    
    if df_c is None:
        print(f"❌ Error: No se encontraron velas para {config.SYMBOL}")
        return

    # Filtramos por fecha
    df_c = df_c.filter(pl.col("time") >= start_date)
    
    # Ticks (CVD)
    print("2. Descargando ticks para reconstruir CVD (paciencia)...")
    df_t = data_loader.get_ticks(config.SYMBOL, start_date, end_date)
    
    if df_t is None:
        print("❌ Error: No se encontraron ticks (o tardó demasiado).")
        return

    # 3. Recalcular Señales
    print("3. La IA está re-analizando el pasado...")
    cvd = indicators.calculate_synthetic_cvd(df_t, config.TIMEFRAME_POLARS)
    df = feature_engineering.create_dataset(df_c, cvd)
    
    if df.is_empty():
        print("⚠️ Advertencia: El dataset generado está vacío.")
        return

    # Pasar a Pandas para graficar
    df_pd = df.to_pandas()
    
    # Generar predicciones masivas
    cols = ['z_score', 'trfi', 'cvd_slope', 'momentum_3', 'volatility']
    model = ai_logic.load_model()
    
    # Predecir todo el dataframe de una vez
    predictions = model.predict(df_pd[cols])
    df_pd['ai_signal'] = predictions

    # 4. Visualización
    print("4. Generando gráfico...")
    
    # Preparar segmentos de colores
    df_pd['date_num'] = mdates.date2num(df_pd['time'])
    x = df_pd['date_num'].values
    y = df_pd['close'].values
    z = df_pd['ai_signal'].values
    
    points = np.array([x, y]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)
    
    # Mapa: Rojo (Venta), Gris (Nada), Verde (Compra)
    cmap = ListedColormap(['#ff4444', 'lightgray', '#00cc00'])
    norm = BoundaryNorm([-1.5, -0.5, 0.5, 1.5], cmap.N)
    
    lc = LineCollection(segments, cmap=cmap, norm=norm)
    lc.set_array(z)
    lc.set_linewidth(1.5)
    
    # Plot
    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(12, 7), 
                                   gridspec_kw={'height_ratios': [3, 1]})
    
    # Precio Coloreado
    ax1.add_collection(lc)
    ax1.autoscale_view()
    ax1.set_title(f'Evaluación IA: {config.SYMBOL} (Verde=Compra, Rojo=Venta)')
    ax1.grid(True, alpha=0.2)
    
    # CVD Line
    ax2.plot(df_pd['time'], df_pd['cvd'], color='purple', lw=1, label='CVD Sintético')
    ax2.legend()
    ax2.grid(True, alpha=0.2)
    
    # Formato fecha
    ax1.xaxis_date()
    fig.autofmt_xdate()
    
    print("✅ Gráfico generado.")
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    plot_review()