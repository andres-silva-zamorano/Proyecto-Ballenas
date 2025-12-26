import time
import os
import polars as pl
from colorama import init, Fore, Back, Style
from src.connection.mt5_connector import MT5Connector
from src.features.indicators import TechnicalIndicators
from src.analysis.microstructure import MicrostructureAnalyzer
from src.utils.logger import DataLogger
from src.models.predictor import MarketPredictor  # <--- NUEVO IMPORT

# --- CONFIGURACIÓN ---
SYMBOL = "BTCUSD"   # Asegúrate que este sea el símbolo activo que detectamos antes
TIMEFRAME_MACRO = 1 # M1 (1 minuto)
MIN_TICKS_MICRO = 30 # Tics mínimos para calcular presión
LOG_FILENAME = "sesion_ballenas.csv"

# Mapa de Regímenes para mostrar texto en vez de números
REGIMEN_MAP = {
    0: "LATERAL (Rango)",
    1: "ALCISTA (Débil)",
    2: "BAJISTA (Débil)",
    3: "ALCISTA (Volátil)",
    4: "BAJISTA (Volátil)",
    5: "TENDENCIA ALCISTA FUERTE 🚀",
    6: "TENDENCIA BAJISTA FUERTE 🔻"
}

def limpiar_consola():
    os.system('cls' if os.name == 'nt' else 'clear')

def render_dashboard(micro, macro, df_ticks, grabando, ia_data):
    limpiar_consola()
    
    # --- HEADER ---
    rec_icon = f"{Back.RED}{Fore.WHITE} ● REC {Style.RESET_ALL}" if grabando else f"{Fore.BLACK}{Back.WHITE} PAUSA {Style.RESET_ALL}"
    titulo = f" BALLENAS IA | {SYMBOL} | Tics: {micro.get('tick_count', 0)} "
    print(Fore.WHITE + Back.BLUE + Style.BRIGHT + titulo.ljust(60) + Style.RESET_ALL + " " + rec_icon)
    print("-" * 70)
    
    # --- SECCIÓN 1: INTELIGENCIA ARTIFICIAL (NUEVO) ---
    if ia_data and "regimen" in ia_data:
        reg_id = ia_data["regimen"]
        probs = ia_data["probs"]
        confianza = probs[reg_id] * 100
        
        # Color según el régimen
        color_ia = Fore.WHITE
        if reg_id in [5, 3, 1]: color_ia = Fore.GREEN
        if reg_id in [6, 4, 2]: color_ia = Fore.RED
        if reg_id == 0: color_ia = Fore.YELLOW
        
        reg_nombre = REGIMEN_MAP.get(reg_id, "Desconocido")
        
        print(f"🧠 {Style.BRIGHT}CEREBRO IA:{Style.RESET_ALL}")
        print(f"   Detección : {color_ia}{Style.BRIGHT}{reg_nombre}{Style.RESET_ALL}")
        print(f"   Confianza : {color_ia}{confianza:.1f}%{Style.RESET_ALL}")
        
        # Mostrar barra de probabilidad simplificada
        print(f"   Prob. Bull: {(probs[5]+probs[3]+probs[1])*100:.0f}% | Prob. Bear: {(probs[6]+probs[4]+probs[2])*100:.0f}%")
    else:
        print(Fore.YELLOW + "🧠 IA: Esperando datos suficientes para pensar...")

    print("-" * 70)

    # --- SECCIÓN 2: CONTEXTO MACRO ---
    if macro:
        precio = macro.get('Close_Price', 0.0)
        ema = macro.get('EMA_Princ', 0.0)
        atr = macro.get('ATR_Act', 0.0)
        rsi = macro.get('RSI_Val', 0.0)
        
        print(f"📊 {Style.BRIGHT}MACRO (M1):{Style.RESET_ALL}")
        print(f"   Precio    : {Fore.CYAN}{precio:.2f}{Style.RESET_ALL}")
        print(f"   EMA Trend : {Fore.YELLOW}{ema:.2f}{Style.RESET_ALL}")
        print(f"   RSI       : {rsi:.1f}") 
    else:
        print("Cargando indicadores macro...")

    print("-" * 70)
    
    # --- SECCIÓN 3: MICROESTRUCTURA (BALLENAS) ---
    if micro["status"] == "EMPTY":
        print(Fore.RED + "Esperando flujo de ticks...")
        return

    desbalance = micro['desbalance']
    
    # Visualización de barra
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

def main():
    init() # Colorama
    
    # 1. Inicializar Módulos
    connector = MT5Connector()
    tech_ind = TechnicalIndicators()
    micro_analyzer = MicrostructureAnalyzer()
    logger = DataLogger(LOG_FILENAME)
    predictor = MarketPredictor() # <--- INICIALIZAMOS EL CEREBRO
    
    if not connector.conectar():
        return

    print("Iniciando Monitor con IA... (Ctrl+C para salir)")
    time.sleep(1)

    try:
        while True:
            # A. Obtener Datos Crudos
            df_ticks = connector.obtener_ticks_recientes(SYMBOL, num_ticks=1000)
            df_velas = connector.obtener_velas_recientes(SYMBOL, num_velas=500) # Necesitamos historia para la IA

            # B. Análisis Micro (Ballenas)
            metrics_micro = micro_analyzer.analizar_flujo(df_ticks)

            # C. Análisis Macro (Indicadores)
            metrics_macro = {}
            if df_velas.height > 300:
                metrics_macro = tech_ind.calcular_features(df_velas)

            # D. PREDICCIÓN DE IA (CEREBRO)
            ia_result = {}
            if metrics_macro:
                regimen_id, probs = predictor.predecir(metrics_macro)
                
                # Guardamos resultado para mostrar y para el logger
                ia_result = {
                    "regimen": regimen_id,
                    "probs": probs
                }
                
                # INYECTAMOS LA IA EN EL MACRO PARA QUE EL LOGGER LO GUARDE
                # Así el CSV se sigue alimentando con las probabilidades en vivo
                metrics_macro["Regimen_Actual"] = regimen_id
                for i, p in enumerate(probs):
                    metrics_macro[f"prob_regimen_{i}"] = p

            # E. Guardar Datos (Logger)
            # Solo grabamos si tenemos datos completos
            if metrics_macro and metrics_micro["status"] == "OK":
                ts_now = df_ticks.select(pl.col("timestamp_ms").last()).item()
                logger.guardar_snapshot(ts_now, metrics_micro, metrics_macro, df_ticks)
                grabando = True
            else:
                grabando = False

            # F. Visualizar
            render_dashboard(metrics_micro, metrics_macro, df_ticks, grabando, ia_result)

            time.sleep(1) # Actualización cada segundo

    except KeyboardInterrupt:
        print("\nApagando monitor...")
        connector.desconectar()
        print("Bye.")

if __name__ == "__main__":
    main()