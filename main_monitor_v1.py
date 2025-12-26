import time
import sys
import os
from colorama import Fore, Back, Style, init

# --- IMPORTACIONES DE MÓDULOS DEL PROYECTO ---
from src.connection.mt5_connector import MT5Connector
from src.features.tick_processor import TickProcessor
from src.features.indicators import TechnicalIndicators
from src.utils.logger import DataLogger  # <--- Módulo de Memoria

# --- CONFIGURACIÓN GLOBAL ---
SYMBOL = "BTCUSD"        # IMPORTANTE: Ajustar según tu broker (ej. BTCUSDm, Bitcoin)
WINDOW_TICKS = 1000      # Ventana de análisis de flujo de órdenes
WINDOW_VELAS = 300       # Ventana de velas para cálculo de EMAs/ATR
REFRESH_RATE = 1         # Segundos entre actualizaciones (Frecuencia de muestreo)
LOG_FILENAME = "sesion_ballenas.csv" # Nombre del archivo donde se guardarán los datos

# Inicializar colorama
init(autoreset=True)

def limpiar_consola():
    """Limpia la terminal para mantener el dashboard estático."""
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    limpiar_consola()
    print(Fore.CYAN + Style.BRIGHT + "--- INICIANDO SISTEMA PROYECTO BALLENAS v1.0-alpha ---")
    
    # 1. INICIALIZACIÓN DE MÓDULOS
    try:
        connector = MT5Connector()
        processor = TickProcessor()
        indicators = TechnicalIndicators()
        logger = DataLogger(LOG_FILENAME) # Inicializamos la grabadora
        print(Fore.GREEN + f"[OK] Sistema de archivos listo. Grabando en: data/raw/{LOG_FILENAME}")
    except Exception as e:
        print(Fore.RED + f"[FATAL] Error cargando módulos: {e}")
        return

    # 2. CONEXIÓN A MT5
    if not connector.conectar():
        print(Fore.RED + "Error crítico: No se pudo conectar a MT5. Revisa que la terminal esté abierta.")
        return

    print(Fore.GREEN + f"Conexión establecida. Escaneando símbolo: {SYMBOL}...")
    time.sleep(1)

    # 3. BUCLE PRINCIPAL (LOOP INFINITO)
    try:
        while True:
            # --- A. OBTENCIÓN DE DATOS MICRO (TICKS) ---
            # Analizamos la presión inmediata de compra/venta
            df_ticks = connector.obtener_ticks_recientes(SYMBOL, num_ticks=WINDOW_TICKS)
            metrics_micro = processor.procesar_flujo(df_ticks)
            
            # --- B. OBTENCIÓN DE DATOS MACRO (VELAS) ---
            # Analizamos el contexto (Tendencia y Volatilidad)
            df_velas = connector.obtener_velas_recientes(SYMBOL, num_velas=WINDOW_VELAS)
            metrics_macro = indicators.calcular_features(df_velas)

            # --- C. GRABACIÓN DE DATOS (LOGGER) ---
            # Si hay datos válidos, guardamos una foto (snapshot) de este segundo
            grabando = False
            if not df_ticks.is_empty() and metrics_macro:
                ts_ms = df_ticks["timestamp_ms"][-1]
                logger.guardar_snapshot(ts_ms, metrics_micro, metrics_macro, df_ticks)
                grabando = True

            # --- D. VISUALIZACIÓN (DASHBOARD) ---
            render_dashboard(metrics_micro, metrics_macro, df_ticks, grabando)
            
            # --- E. CONTROL DE TIEMPO ---
            time.sleep(REFRESH_RATE)

    except KeyboardInterrupt:
        # Salida limpia al presionar Ctrl+C
        print(Fore.YELLOW + "\n\n[SISTEMA] Interrupción detectada.")
        print(Fore.YELLOW + "[SISTEMA] Cerrando conexión y guardando archivos...")
        connector.desconectar()
        print(Fore.CYAN + "Sistema apagado correctamente.")
        sys.exit(0)
        
    except Exception as e:
        print(Fore.RED + f"\n[ERROR CRÍTICO EN LOOP]: {e}")
        connector.desconectar()

def render_dashboard(micro, macro, df_ticks, grabando):
    limpiar_consola()
    
    # Header
    rec_icon = f"{Back.RED}{Fore.WHITE} ● REC {Style.RESET_ALL}" if grabando else f"{Fore.BLACK}{Back.WHITE} PAUSA {Style.RESET_ALL}"
    titulo = f" BALLENAS MONITOR | {SYMBOL} | Tics: {micro.get('tick_count', 0)} "
    print(Fore.WHITE + Back.BLUE + Style.BRIGHT + titulo.ljust(60) + Style.RESET_ALL + " " + rec_icon)
    print("-" * 70)
    
    # --- SECCIÓN 1: CONTEXTO MACRO (Ajustado a nuevas Keys) ---
    if macro:
        # Nota: Ya no tenemos "tendencia" calculado en texto, lo inferimos rápido aquí
        precio = macro.get('Close_Price', 0.0)
        ema_princ = macro.get('EMA_Princ', 0.0) # EMA 80
        atr = macro.get('ATR_Act', 0.0)
        rsi = macro.get('RSI_Val', 0.0)
        
        tendencia = "NEUTRAL"
        if precio > ema_princ: tendencia = "ALCISTA"
        if precio < ema_princ: tendencia = "BAJISTA"
        
        color_t = Fore.GREEN if "ALCISTA" in tendencia else (Fore.RED if "BAJISTA" in tendencia else Fore.YELLOW)
        
        print(f"Tendencia    : {color_t}{Style.BRIGHT}{tendencia}{Style.RESET_ALL} (Sobre EMA Principal)")
        print(f"Precio       : {Fore.CYAN}{precio:.2f}{Style.RESET_ALL}")
        print(f"Indicadores  : RSI {rsi:.1f} | ATR {atr:.2f} | MACD {macro.get('MACD_Val', 0):.2f}")
    else:
        print(Fore.YELLOW + "Cargando indicadores (Necesitamos +300 velas)...")

    print("-" * 70)
    
    # --- SECCIÓN 2: FLUJO DE ÓRDENES MICRO (Igual que antes) ---
    if micro["status"] == "EMPTY":
        print(Fore.RED + "Esperando flujo de ticks suficiente...")
        return

    desbalance = micro['desbalance']
    intensidad = micro.get('intensidad', 0)
    
    bar_length = 30
    normalized_pos = int((desbalance + 1) / 2 * bar_length)
    normalized_pos = max(0, min(bar_length - 1, normalized_pos))
    
    barra = ["-"] * bar_length
    color_state = Fore.WHITE
    estado_txt = "NEUTRAL"
    marcador = "|"
    
    if desbalance > 0.15:
        color_state = Fore.GREEN
        estado_txt = "PRESIÓN COMPRA"
        marcador = "▲"
    elif desbalance < -0.15:
        color_state = Fore.RED
        estado_txt = "PRESIÓN VENTA"
        marcador = "▼"
        
    barra[normalized_pos] = f"{Style.BRIGHT}{marcador}{Style.RESET_ALL}{color_state}"
    barra_str = "".join(barra)

    print(f"Flujo Tics   : {color_state}{estado_txt}{Style.RESET_ALL}")
    print(f"Score Delta  : {desbalance:.4f} (Intensidad: {intensidad:.2f})")
    print(f"Balance      : [{color_state}{barra_str}{Style.RESET_ALL}]")
    print("-" * 70)

    # Debug último tick
    if not df_ticks.is_empty():
        last = df_ticks.tail(1)
        print(f"{Fore.LIGHTBLACK_EX}Last Tick: {last['timestamp_ms'][0]} | Bid: {last['bid'][0]}{Style.RESET_ALL}")

if __name__ == "__main__":
    main()