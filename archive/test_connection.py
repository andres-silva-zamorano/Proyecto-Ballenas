import MetaTrader5 as mt5
from src.connection.mt5_connector import MT5Connector
import time
from colorama import Fore, Style, init

# Inicializar colorama
init()

def run_test():
    print(Fore.CYAN + "--- INICIANDO TEST DE CONECTIVIDAD MT5 + POLARS ---" + Style.RESET_ALL)
    
    connector = MT5Connector() # Asume que tu terminal MT5 ya tiene la cuenta logueada
    
    if connector.conectar():
        print(Fore.GREEN + f"[OK] Conectado a MT5 versión: {mt5.version()}" + Style.RESET_ALL)
        
        symbol = "BTCUSD" # Ajustar según tu broker (ej. BTCUSDm, Bitcoin, etc.)
        print(f"Solicitando ticks para: {symbol}...")
        
        df = connector.obtener_ticks_recientes(symbol, num_ticks=10)
        
        if not df.is_empty():
            print(Fore.YELLOW + "\n[DATA CHECK] Últimos 5 ticks (Formato Polars):" + Style.RESET_ALL)
            print(df.tail(5))
            
            # Verificación de tipos
            print(f"\nTipo de objeto retornado: {type(df)}")
            print(Fore.GREEN + "[OK] Test superado. Polars está en control." + Style.RESET_ALL)
        else:
            print(Fore.RED + "[ERROR] Dataframe vacío. Revisa el nombre del símbolo." + Style.RESET_ALL)
            
        connector.desconectar()
    else:
        print(Fore.RED + "[FATAL] No se pudo conectar a MT5." + Style.RESET_ALL)

if __name__ == "__main__":
    run_test()