import sys
import os
import time
import csv
from datetime import datetime
from colorama import init, Fore, Back, Style
import polars as pl
import pandas as pd
import pandas_ta as ta
import MetaTrader5 as mt5_lib # <--- NECESARIO: Para obtener el tick directo

# --- 1. CORRECCIÓN DE RUTAS ---
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# --- 2. IMPORTACIONES ---
from src.connection.mt5_connector import MT5Connector
from src.features.microstructure import MicrostructureAnalyzer 
from src.utils.logger import DataLogger
from src.models.predictor import MarketPredictor

init(autoreset=True)

# --- CONFIGURACIÓN ---
SYMBOL = "BTCUSD"
TIMEFRAME = mt5_lib.TIMEFRAME_M1 # Usamos la constante de la librería
HISTORY_BARS = 1000 

REGIMEN_MAP = {
    0: "LATERAL",
    1: "ALCISTA (D)",
    2: "BAJISTA (D)",
    3: "ALCISTA (V)",
    4: "BAJISTA (V)",
    5: "ALCISTA (F)",
    6: "BAJISTA (F)"
}

# --- CÁLCULO INDICADORES ---
def calcular_indicadores_macro(df_pandas):
    try:
        df = df_pandas.copy()
        df['EMA_Princ'] = ta.ema(df['close'], length=80)
        df['RSI_Val'] = ta.rsi(df['close'], length=14)
        df['ATR_Act'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        try:
            adx_df = ta.adx(df['high'], df['low'], df['close'], length=14)
            if adx_df is not None:
                 col_adx = [c for c in adx_df.columns if c.startswith('ADX')][0]
                 df['ADX_Val'] = adx_df[col_adx]
            else:
                 df['ADX_Val'] = 0
        except:
            df['ADX_Val'] = 0
        df.fillna(0, inplace=True)
        df['Close_Price'] = df['close']
        return df
    except Exception as e:
        print(f"Error calculando indicadores: {e}")
        return df_pandas

# --- VISUALIZACIÓN ---
def limpiar_consola():
    os.system('cls' if os.name == 'nt' else 'clear')

def render_dashboard(micro, macro, grabando, ia_data):
    limpiar_consola()
    
    tics_analizados = micro.get('intensidad', 0)
    
    rec_icon = f"{Back.RED}{Fore.WHITE} ● REC {Style.RESET_ALL}" if grabando else f"{Fore.BLACK}{Back.WHITE} PAUSA {Style.RESET_ALL}"
    titulo = f" BALLENAS IA | {SYMBOL} | Tics(Win): {tics_analizados} "
    print(Fore.WHITE + Back.BLUE + Style.BRIGHT + titulo.ljust(60) + Style.RESET_ALL + " " + rec_icon)
    print("-" * 70)
    
    # SECCIÓN 1: IA
    if ia_data and "regimen" in ia_data:
        reg_id = ia_data["regimen"]
        probs = ia_data["probs"]
        confianza = probs[reg_id] * 100
        
        color_ia = Fore.WHITE
        if reg_id in [5, 3, 1]: color_ia = Fore.GREEN
        if reg_id in [6, 4, 2]: color_ia = Fore.RED
        if reg_id == 0: color_ia = Fore.YELLOW
        
        reg_nombre = REGIMEN_MAP.get(reg_id, "Desconocido")
        
        print(f"🧠 {Style.BRIGHT}CEREBRO IA:{Style.RESET_ALL}")
        print(f"   Decisión Final: {color_ia}{Style.BRIGHT}{reg_nombre}{Style.RESET_ALL} (Confianza: {confianza:.1f}%)")
        print(f"   {Fore.BLACK}{Back.WHITE} DEBATE INTERNO (Probabilidades): {Style.RESET_ALL}")
        
        def fmt_prob(idx, nombre, color_base):
            p = probs[idx] * 100
            estilo = Style.BRIGHT if idx == reg_id else ""
            marcador = "◄ WIN" if idx == reg_id else ""
            barra = "|" * int(p / 5) 
            return f"{color_base}{estilo}[{idx}] {nombre:<10}: {p:5.1f}% {barra} {marcador}{Style.RESET_ALL}"

        print(fmt_prob(0, "LATERAL", Fore.YELLOW))
        print("-" * 40)
        print(fmt_prob(1, "ALCISTA (D)", Fore.GREEN))
        print(fmt_prob(3, "ALCISTA (V)", Fore.GREEN))
        print(fmt_prob(5, "ALCISTA (F)", Fore.GREEN))
        print("-" * 40)
        print(fmt_prob(2, "BAJISTA (D)", Fore.RED))
        print(fmt_prob(4, "BAJISTA (V)", Fore.RED))
        print(fmt_prob(6, "BAJISTA (F)", Fore.RED))
    else:
        print(Fore.YELLOW + "🧠 IA: Esperando datos suficientes para pensar...")

    print("-" * 70)

    # SECCIÓN 2: MACRO
    if macro:
        precio = macro.get('Close_Price', 0.0)
        ema = macro.get('EMA_Princ', 0.0)
        rsi = macro.get('RSI_Val', 0.0)
        print(f"📊 {Style.BRIGHT}MACRO (M1):{Style.RESET_ALL}")
        print(f"   Precio    : {Fore.CYAN}{precio:.2f}{Style.RESET_ALL}")
        print(f"   EMA Trend : {Fore.YELLOW}{ema:.2f}{Style.RESET_ALL}")
        print(f"   RSI       : {rsi:.1f}") 
    else:
        print("Cargando indicadores macro...")

    print("-" * 70)
    
    # SECCIÓN 3: MICRO
    if micro.get("status") == "EMPTY":
        print(Fore.RED + "Esperando flujo de ticks...")
        return

    desbalance = micro.get('desbalance', 0.0)
    bar_length = 30
    normalized_pos = int((desbalance + 1) / 2 * bar_length)
    normalized_pos = max(0, min(bar_length - 1, normalized_pos))
    
    barra = ["-"] * bar_length
    color_state = Fore.WHITE
    estado_txt = "NEUTRAL"
    marcador = "|"
    
    if desbalance > 0.15:
        color_state = Fore.GREEN
        estado_txt = "COMPRA INST."
        marcador = "▲"
    elif desbalance < -0.15:
        color_state = Fore.RED
        estado_txt = "VENTA INST."
        marcador = "▼"
        
    barra[normalized_pos] = f"{Style.BRIGHT}{marcador}{Style.RESET_ALL}{color_state}"
    barra_str = "".join(barra)

    print(f"🐋 {Style.BRIGHT}MICRO (Flow):{Style.RESET_ALL}")
    print(f"   Estado    : {color_state}{estado_txt}{Style.RESET_ALL}")
    print(f"   Score     : {desbalance:.4f}")
    print(f"   Balance   : [{color_state}{barra_str}{Style.RESET_ALL}]")
    print("-" * 70)

# --- MAIN ---
def main():
    print("Iniciando Sistema Ballenas IA...")
    
    # CORRECCIÓN 1: Instancia sin argumentos (Tu __init__ no pide symbol)
    mt5_con = MT5Connector() 
    if not mt5_con.conectar(): return

    micro_analyzer = MicrostructureAnalyzer() 
    logger = DataLogger() 
    predictor = MarketPredictor() 
    
    if not predictor.cargar_modelos():
        print(Fore.RED + "ADVERTENCIA: No se encontraron modelos IA.")
        time.sleep(2)
    
    print("Sincronizando histórico...")
    # CORRECCIÓN 2: Usar 'obtener_velas_recientes' que SÍ existe en tu conector
    # Convertimos Polars a Pandas para el cálculo de indicadores
    df_pl = mt5_con.obtener_velas_recientes(SYMBOL, timeframe=TIMEFRAME, num_velas=HISTORY_BARS)
    
    if df_pl is None or df_pl.height == 0:
        print("Error: No se pudo obtener histórico inicial.")
        return
        
    df_raw = df_pl.to_pandas()

    print(Fore.GREEN + "Sistema EN LÍNEA. Escuchando mercado...")
    time.sleep(1)

    try:
        grabando = False
        ultimo_segundo = 0
        df_ticks_acumulado = pl.DataFrame()

        while True:
            # CORRECCIÓN 3: Tu conector NO tiene 'obtener_tick_actual'.
            # Usamos la librería mt5 directa ya que la conexión está abierta.
            tick_raw = mt5_lib.symbol_info_tick(SYMBOL)
            
            if tick_raw:
                # Convertimos el tick raw a diccionario compatible
                tick = tick_raw._asdict()
                
                # 1. ACUMULAR TICK
                nuevo_tick = pl.DataFrame({
                    "time": [tick['time']], 
                    "bid": [tick['bid']], 
                    "ask": [tick['ask']], 
                    "flags": [tick['flags']],
                    "timestamp_ms": [int(time.time() * 1000)]
                })
                
                try:
                    df_ticks_acumulado = pl.concat([df_ticks_acumulado, nuevo_tick])
                    if df_ticks_acumulado.height > 1000:
                        df_ticks_acumulado = df_ticks_acumulado.tail(1000)
                except:
                    df_ticks_acumulado = nuevo_tick

                # 2. PROCESAR MICRO
                metrics_micro = micro_analyzer.analizar_flujo(df_ticks_acumulado)

                # 3. MACROESTRUCTURA
                ts_actual = int(tick['time'])
                metrics_macro = {}
                ia_result = {}
                
                if ts_actual > ultimo_segundo:
                    # CORRECCIÓN: Usar tu nombre de método real
                    df_new_pl = mt5_con.obtener_velas_recientes(SYMBOL, timeframe=TIMEFRAME, num_velas=200)
                    
                    if df_new_pl is not None and df_new_pl.height > 0:
                        df_new = df_new_pl.to_pandas()
                        df_indicators = calcular_indicadores_macro(df_new)
                        last_row = df_indicators.iloc[-1].to_dict()
                        metrics_macro = last_row
                        
                        prediccion = predictor.predecir_tiempo_real(last_row)
                        if prediccion:
                            metrics_macro["Regimen_Actual"] = prediccion["regimen"]
                            metrics_macro["probs"] = prediccion["probs"]
                            for i, p in enumerate(prediccion["probs"]):
                                metrics_macro[f"prob_regimen_{i}"] = p
                            ia_result = prediccion
                    
                    ultimo_segundo = ts_actual

                    # 4. RENDERIZAR
                    render_dashboard(metrics_micro, metrics_macro, grabando, ia_result)

                    # 5. GUARDAR
                    if metrics_macro and metrics_micro.get("status") == "OK":
                        ts_ms = int(time.time() * 1000)
                        
                        logger.guardar_snapshot(ts_ms, metrics_micro, metrics_macro, df_ticks_acumulado)
                        
                        lite_path = os.path.join("data", "raw", "live_lite.csv")
                        row_lite = [
                            ts_ms,
                            metrics_macro.get("Close_Price", 0),
                            metrics_macro.get("EMA_Princ", 0),
                            metrics_micro.get("desbalance", 0),
                            ia_result.get("regimen", 0)
                        ]
                        try:
                            file_exists = os.path.exists(lite_path)
                            with open(lite_path, mode='a', newline='') as f:
                                writer = csv.writer(f)
                                if not file_exists:
                                    writer.writerow(["Timestamp", "Close_Price", "EMA_Princ", "Micro_Score", "Regimen_Actual"])
                                writer.writerow(row_lite)
                        except: pass
                        
                        grabando = True

            time.sleep(0.01)

    except KeyboardInterrupt:
        mt5_con.desconectar()
        print("\nMonitor detenido.")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        if 'mt5_con' in locals(): mt5_con.desconectar()

if __name__ == "__main__":
    main()