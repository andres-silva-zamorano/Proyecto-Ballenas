import MetaTrader5 as mt5
import pandas as pd
import os
import sys
import time

# Ajusta esto si tu carpeta está en otro lado
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from src.features.indicators import TechnicalIndicators
import polars as pl

# CONFIGURACIÓN
SYMBOL = "BTCUSD"
TIMEFRAME = mt5.TIMEFRAME_M1
BARS_COUNT = 100000  # ~70 días de datos
OUTPUT_FILE = os.path.join("data", "raw", "historial_completo.csv")

def descargar_y_procesar():
    print(f"--- 📥 DESCARGANDO {BARS_COUNT} VELAS DE {SYMBOL} ---")
    
    # 1. Inicializar MT5
    if not mt5.initialize():
        print(f"❌ Error iniciando MT5: {mt5.last_error()}")
        return

    # 2. Forzar selección del símbolo (CRUCIAL)
    # Esto asegura que esté en 'Observación de Mercado' y descargue datos
    if not mt5.symbol_select(SYMBOL, True):
        print(f"❌ Error: No se pudo seleccionar el símbolo '{SYMBOL}'.")
        print("   -> Verifica que el nombre sea exacto (ej. BTCUSD, BTCUSDm, Bitcoin).")
        print(f"   -> Error interno: {mt5.last_error()}")
        mt5.shutdown()
        return

    # Esperar un momento para que MT5 sincronice si es necesario
    print("⏳ Sincronizando símbolo con el servidor...")
    time.sleep(1)

    # 3. Descargar Raw
    # Primero probamos con pocas velas para ver si hay conexión
    check = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, 10)
    if check is None:
        print("❌ Error CRÍTICO: MT5 no devuelve datos.")
        print(f"   -> Código de error MT5: {mt5.last_error()}")
        mt5.shutdown()
        return

    # Si la prueba pasó, descargamos todo el bloque
    print(f"✅ Conexión verificada. Descargando bloque masivo ({BARS_COUNT})...")
    rates = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, BARS_COUNT)
    mt5.shutdown()
    
    if rates is None or len(rates) == 0:
        print("❌ Falló la descarga masiva (retornó vacío). Intenta con menos velas.")
        return

    print(f"✅ Descargados {len(rates)} registros. Procesando indicadores...")

    # 4. Procesamiento (Simulación de Micro Score)
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    
    # Renombrar
    df = df.rename(columns={
        'time': 'Timestamp', 
        'close': 'Close_Price',
        'tick_volume': 'Vol'
    })
    
    # ⚠️ SIMULACIÓN DE MICRO SCORE (Proxy para Backtesting)
    # Usamos la relación Precio/Volumen para estimar dónde hubo ballenas en el pasado
    df['delta'] = df['Close_Price'] - df['open']
    df['range'] = df['high'] - df['low']
    # Evitamos división por cero
    denom = df['range'].replace(0, 0.00001)
    
    # Score Proxy: (Cuerpo / Rango) * (Volumen / PromedioVolumen)
    vol_promedio = df['Vol'].rolling(20).mean().fillna(df['Vol'])
    df['Micro_Score'] = (df['delta'] / denom) * (df['Vol'] / vol_promedio)
    
    # Normalizar entre -1 y 1
    df['Micro_Score'] = df['Micro_Score'].clip(-1, 1)
    
    # Limpiar columnas no deseadas
    df = df.fillna(0)
    
    # Guardar
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"💾 Archivo guardado: {OUTPUT_FILE}")
    print("👉 AHORA: Ve a 'src/models/optimize_strategy.py' y asegúrate de que apunte a este archivo.")

if __name__ == "__main__":
    descargar_y_procesar()