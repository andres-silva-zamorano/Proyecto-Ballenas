import MetaTrader5 as mt5

if not mt5.initialize():
    print("Error MT5")
else:
    symbol = "BTCUSD" # Ojo con el nombre
    info = mt5.symbol_info(symbol)
    
    if info:
        print(f"--- INFO BROKER: {symbol} ---")
        print(f"Volumen Mínimo: {info.volume_min}")
        print(f"Volumen Máximo: {info.volume_max}")
        print(f"Paso de Volumen: {info.volume_step}")
        print(f"Modo Filling (Raw): {info.filling_mode}")
        print("-----------------------------")
    else:
        print(f"No encuentro el símbolo '{symbol}'")
    
    mt5.shutdown()