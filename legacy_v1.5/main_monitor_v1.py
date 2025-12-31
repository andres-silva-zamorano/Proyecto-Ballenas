import sys
import os
import time
import csv
from datetime import datetime
from colorama import init, Fore, Back, Style
import polars as pl
import MetaTrader5 as mt5_lib 

# --- 1. CONFIGURACIÓN DE RUTAS ---
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# --- 2. IMPORTACIONES ---
from src.connection.mt5_connector import MT5Connector
from src.features.microstructure import MicrostructureAnalyzer 
from src.features.indicators import TechnicalIndicators 
from src.utils.logger import DataLogger
from src.models.predictor import MarketPredictor
from src.strategies.whale_detector import WhaleDetector
from src.execution.trader import MT5Trader

init(autoreset=True)

# --- CONFIGURACIÓN GENERAL ---
SYMBOL = "BTCUSD"
TIMEFRAME = mt5_lib.TIMEFRAME_M1 
HISTORY_BARS = 1000 

# --- PARÁMETROS GESTIÓN DE RIESGO (GOLDEN MEAN - PROMEDIO OPTIMIZADO) ---
# Estos valores equilibran la agresividad y la seguridad según tus pruebas
LOT_SIZE = 0.01          
MAGIC_NUMBER = 555777    
OPTUNA_STOP_LOSS = 0.006   # 0.6%
OPTUNA_TAKE_PROFIT = 0.011 # 1.1%

REGIMEN_MAP = {
    0: "LATERAL",
    1: "ALCISTA (D)", 2: "BAJISTA (D)",
    3: "ALCISTA (V)", 4: "BAJISTA (V)",
    5: "ALCISTA (F)", 6: "BAJISTA (F)"
}

# --- VISUALIZACIÓN ---
def limpiar_consola():
    os.system('cls' if os.name == 'nt' else 'clear')

def render_dashboard(micro, macro, grabando, ia_data, estado_trading):
    limpiar_consola()
    
    # 1. HEADER (Estado del Sistema)
    tics = micro.get('intensidad', 0)
    estatus_bot = f"{Back.GREEN}{Fore.WHITE} BOT ACTIVO {Style.RESET_ALL}" if estado_trading else f"{Back.YELLOW}{Fore.BLACK} SOLO MONITOR {Style.RESET_ALL}"
    rec_icon = f"{Back.RED}{Fore.WHITE} ● REC {Style.RESET_ALL}" if grabando else f"{Fore.BLACK}{Back.WHITE} PAUSA {Style.RESET_ALL}"
    
    titulo = f" BALLENAS IA | {SYMBOL} | Tics: {tics} "
    print(Fore.WHITE + Back.BLUE + Style.BRIGHT + titulo.ljust(60) + Style.RESET_ALL + " " + estatus_bot + " " + rec_icon)
    print("-" * 80)
    
    # 2. SECCIÓN IA (Cerebro Completo)
    if ia_data and "regimen" in ia_data:
        reg_id = ia_data["regimen"]
        probs = ia_data["probs"]
        confianza = probs[reg_id] * 100
        
        # Color según sentimiento
        color_ia = Fore.WHITE
        if reg_id in [5, 3, 1]: color_ia = Fore.GREEN
        if reg_id in [6, 4, 2]: color_ia = Fore.RED
        if reg_id == 0: color_ia = Fore.YELLOW
        
        reg_nombre = REGIMEN_MAP.get(reg_id, "Desconocido")
        
        print(f"🧠 {Style.BRIGHT}CEREBRO IA:{Style.RESET_ALL}")
        print(f"   Decisión Final: {color_ia}{Style.BRIGHT}{reg_nombre}{Style.RESET_ALL} (Confianza: {confianza:.1f}%)")
        print(f"   {Fore.BLACK}{Back.WHITE} DEBATE INTERNO (Probabilidades): {Style.RESET_ALL}")
        
        # Barra de probabilidad visual
        def fmt_prob(idx, nombre, color_base):
            p = probs[idx] * 100
            estilo = Style.BRIGHT if idx == reg_id else ""
            marcador = "◄ WIN" if idx == reg_id else ""
            barra = "█" * int(p / 5) 
            return f"{color_base}{estilo}[{idx}] {nombre:<11}: {p:5.1f}% {barra} {marcador}{Style.RESET_ALL}"

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
        print(Fore.YELLOW + "🧠 IA: Recopilando datos para inferencia...")

    print("-" * 80)

    # 3. SECCIÓN MACRO (Indicadores Técnicos)
    precio_actual = 0.0
    if macro:
        precio_actual = macro.get('Close_Price', 0.0)
        ema = macro.get('EMA_Princ', 0.0)
        rsi = macro.get('RSI_Val', 0.0)
        adx = macro.get('ADX_Val', 0.0)
        
        # Colores dinámicos
        c_rsi = Fore.RED if rsi > 70 else Fore.GREEN if rsi < 30 else Fore.WHITE
        c_adx = Fore.GREEN if adx > 25 else Fore.YELLOW
        
        print(f"📊 {Style.BRIGHT}MACRO (M1):{Style.RESET_ALL}")
        print(f"   Precio    : {Fore.CYAN}{precio_actual:.2f}{Style.RESET_ALL}")
        print(f"   EMA Trend : {Fore.YELLOW}{ema:.2f}{Style.RESET_ALL}")
        print(f"   RSI (14)  : {c_rsi}{rsi:.1f}{Style.RESET_ALL}") 
        print(f"   ADX (14)  : {c_adx}{adx:.1f}{Style.RESET_ALL}") 
    else:
        print("Cargando indicadores macro...")

    print("-" * 80)
    
    # 4. SECCIÓN MICRO (Estrategia y Flow)
    if micro.get("status") == "EMPTY":
        print(Fore.RED + "Esperando flujo de ticks...")
        return

    # A. Datos Instantáneos
    desbalance = micro.get('desbalance', 0.0)
    evento = micro.get('evento', "NEUTRAL")
    presion_avg = micro.get('presion_acumulada', 0.0)
    
    # B. Barra Visual de Flow
    bar_length = 40
    normalized_pos = int((desbalance + 1) / 2 * bar_length)
    normalized_pos = max(0, min(bar_length - 1, normalized_pos))
    
    barra = ["-"] * bar_length
    color_state = Fore.WHITE
    marcador = "|"
    
    if desbalance > 0.09: # Usando el umbral Golden Mean visualmente
        color_state = Fore.GREEN
        marcador = "▲"
    elif desbalance < -0.09:
        color_state = Fore.RED
        marcador = "▼"
        
    barra[normalized_pos] = f"{Style.BRIGHT}{marcador}{Style.RESET_ALL}{color_state}"
    barra_str = "".join(barra)

    # C. Lógica de Estrategia y Objetivos (TP/SL)
    msg_color = Fore.WHITE
    msg_texto = f"RECOPILANDO (Presión: {presion_avg:.3f})"
    targets_txt = ""

    if precio_actual > 0:
        # COMPRA
        if evento in ["ABSORCION_COMPRA", "IMPULSO_ALCISTA"]:
            tp_price = precio_actual * (1 + OPTUNA_TAKE_PROFIT)
            sl_price = precio_actual * (1 - OPTUNA_STOP_LOSS)
            targets_txt = f"\n   🎯 TP: {Fore.GREEN}{tp_price:.2f}{Style.RESET_ALL} | 🛡️ SL: {Fore.RED}{sl_price:.2f}{Style.RESET_ALL}"
            
            if evento == "ABSORCION_COMPRA":
                msg_color = Fore.CYAN
                msg_texto = f"🛡️  ABSORCIÓN ALCISTA (Ballenas Comprando)"
            else:
                msg_color = Fore.GREEN
                msg_texto = f"🚀 IMPULSO ALCISTA (Confirmado)"

        # VENTA
        elif evento in ["DISTRIBUCION_VENTA", "IMPULSO_BAJISTA"]:
            tp_price = precio_actual * (1 - OPTUNA_TAKE_PROFIT)
            sl_price = precio_actual * (1 + OPTUNA_STOP_LOSS)
            targets_txt = f"\n   🎯 TP: {Fore.GREEN}{tp_price:.2f}{Style.RESET_ALL} | 🛡️ SL: {Fore.RED}{sl_price:.2f}{Style.RESET_ALL}"

            if evento == "DISTRIBUCION_VENTA":
                msg_color = Fore.MAGENTA
                msg_texto = f"🧱 DISTRIBUCIÓN BAJISTA (Ballenas Vendiendo)"
            else:
                msg_color = Fore.RED
                msg_texto = f"📉 IMPULSO BAJISTA (Confirmado)"
        
        # NEUTRAL
        elif evento == "RANGO_NEUTRAL":
            msg_texto = f"⏸️  NEUTRAL (Sin dirección clara)"

    print(f"🐋 {Style.BRIGHT}MICRO (Estrategia 5m):{Style.RESET_ALL}")
    print(f"   Estado      : {msg_color}{msg_texto}{Style.RESET_ALL} {targets_txt}")
    print(f"   Flow (Inst) : [{color_state}{barra_str}{Style.RESET_ALL}] {desbalance:.2f}")
    print("-" * 80)

# --- BUCLE PRINCIPAL ---
def main():
    print("Iniciando Sistema Ballenas IA (Edición Completa)...")
    
    # 1. Instancias
    mt5_con = MT5Connector() 
    if not mt5_con.conectar(): return

    micro_analyzer = MicrostructureAnalyzer() 
    whale_strategy = WhaleDetector(ventana_segundos=300) 
    technical_calc = TechnicalIndicators() 
    logger = DataLogger() 
    predictor = MarketPredictor() 
    
    # BRAZO ROBÓTICO
    trader = MT5Trader(SYMBOL, LOT_SIZE, MAGIC_NUMBER)
    
    print("Sincronizando histórico...")
    df_raw_pl = mt5_con.obtener_velas_recientes(SYMBOL, timeframe=TIMEFRAME, num_velas=HISTORY_BARS)
    if df_raw_pl is None: return
        
    print(Fore.GREEN + "Sistema EN LÍNEA. Escuchando mercado...")
    time.sleep(1)

    try:
        grabando = False
        ultimo_segundo = 0
        df_ticks_acumulado = pl.DataFrame()
        
        # Control de disparo (Cooldown)
        ultimo_disparo_ts = 0 
        COOLDOWN_SEG = 300 # 5 min entre operaciones

        while True:
            tick_raw = mt5_lib.symbol_info_tick(SYMBOL)
            
            if tick_raw:
                tick = tick_raw._asdict()
                ts_actual_sec = int(time.time())
                
                # 1. Acumular Tick
                nuevo_tick = pl.DataFrame({
                    "time": [tick['time']], "bid": [tick['bid']], "ask": [tick['ask']], 
                    "flags": [tick['flags']], "timestamp_ms": [int(time.time() * 1000)]
                })
                try:
                    df_ticks_acumulado = pl.concat([df_ticks_acumulado, nuevo_tick])
                    if df_ticks_acumulado.height > 1000: df_ticks_acumulado = df_ticks_acumulado.tail(1000)
                except: df_ticks_acumulado = nuevo_tick

                # 2. Análisis Micro
                metrics_micro = micro_analyzer.analizar_flujo(df_ticks_acumulado)
                precio_ask = tick['ask'] # Para comprar
                precio_bid = tick['bid'] # Para vender

                # 3. Estrategia
                tipo_evento, avg_pressure = whale_strategy.detectar_estrategia(ts_actual_sec, metrics_micro.get('desbalance',0), precio_bid)
                metrics_micro['evento'] = tipo_evento
                metrics_micro['presion_acumulada'] = avg_pressure

                # ---------------------------------------------------------
                # 🔥 AUTO-TRADING 🔥
                # ---------------------------------------------------------
                ya_operando = trader.tengo_posicion_abierta()
                
                if not ya_operando and (ts_actual_sec - ultimo_disparo_ts > COOLDOWN_SEG):
                    
                    # COMPRA
                    if tipo_evento in ["ABSORCION_COMPRA", "IMPULSO_ALCISTA"]:
                        tp = precio_ask * (1 + OPTUNA_TAKE_PROFIT)
                        sl = precio_ask * (1 - OPTUNA_STOP_LOSS)
                        
                        print(f"\n🚀 DETECTADO: {tipo_evento}. DISPARANDO COMPRA...")
                        if trader.enviar_orden(mt5_lib.ORDER_TYPE_BUY, precio_ask, sl, tp):
                            ultimo_disparo_ts = ts_actual_sec

                    # VENTA
                    elif tipo_evento in ["DISTRIBUCION_VENTA", "IMPULSO_BAJISTA"]:
                        tp = precio_bid * (1 - OPTUNA_TAKE_PROFIT)
                        sl = precio_bid * (1 + OPTUNA_STOP_LOSS)
                        
                        print(f"\n📉 DETECTADO: {tipo_evento}. DISPARANDO VENTA...")
                        if trader.enviar_orden(mt5_lib.ORDER_TYPE_SELL, precio_bid, sl, tp):
                            ultimo_disparo_ts = ts_actual_sec
                # ---------------------------------------------------------

                # 4. Análisis Macro y Visualización
                ts_candle = int(tick['time'])
                metrics_macro = {}
                ia_result = {}
                
                if ts_candle > ultimo_segundo:
                    df_candles = mt5_con.obtener_velas_recientes(SYMBOL, timeframe=TIMEFRAME, num_velas=1000)
                    if df_candles is not None and df_candles.height > 300:
                        metrics_macro = technical_calc.calcular_features(df_candles)
                        if predictor.loaded and metrics_macro:
                            reg, probs = predictor.predecir(metrics_macro)
                            ia_result = {"regimen": reg, "probs": probs}
                            metrics_macro["Regimen_Actual"] = reg
                            for i, p in enumerate(probs): metrics_macro[f"prob_regimen_{i}"] = p
                    
                    ultimo_segundo = ts_candle
                    render_dashboard(metrics_micro, metrics_macro, grabando, ia_result, ya_operando)

                    if metrics_macro:
                        logger.guardar_snapshot(ts_actual_sec*1000, metrics_micro, metrics_macro, df_ticks_acumulado)
                        grabando = True

            time.sleep(0.01)

    except KeyboardInterrupt:
        mt5_con.desconectar()
        print("\nBot detenido.")
    except Exception as e:
        print(f"\nERROR: {e}")
        mt5_con.desconectar()

if __name__ == "__main__":
    main()