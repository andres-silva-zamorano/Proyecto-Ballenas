import MetaTrader5 as mt5
import time
from datetime import datetime

def escanear_simbolos():
    print("--- ESCÁNER DE SÍMBOLOS DISPONIBLES ---")
    if not mt5.initialize():
        print("Error conectando a MT5")
        return

    # Buscamos todo lo que contenga "BTC"
    # Intenta obtener símbolos que contengan BTC
    simbolos = mt5.symbols_get(group="*BTC*")
    
    if simbolos is None or len(simbolos) == 0:
        # Si falla, intentamos buscar "Bitcoin"
        simbolos = mt5.symbols_get(group="*Bitcoin*")

    if simbolos:
        print(f"{'SÍMBOLO':<15} | {'BID (Venta)':<10} | {'ASK (Compra)':<10} | {'HORA (Ultimo Tic)':<20}")
        print("-" * 65)
        
        for s in simbolos:
            # Seleccionamos el símbolo para asegurar que tengamos datos frescos
            mt5.symbol_select(s.name, True)
            tick = mt5.symbol_info_tick(s.name)
            
            if tick:
                ts = datetime.fromtimestamp(tick.time).strftime('%H:%M:%S')
                print(f"{s.name:<15} | {tick.bid:<10.2f} | {tick.ask:<10.2f} | {ts:<20}")
            else:
                print(f"{s.name:<15} | {'SIN DATOS':<10} | {'-':<10} | {'-'}")
    else:
        print("No se encontraron símbolos con 'BTC' o 'Bitcoin'.")
        print("Revisa en tu MT5 cómo se llama exactamente el activo.")

    mt5.shutdown()

if __name__ == "__main__":
    escanear_simbolos()