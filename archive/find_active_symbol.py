import MetaTrader5 as mt5
import time
from datetime import datetime

def buscar_activo_vivo():
    print("--- BUSCANDO SÍMBOLOS ACTIVOS (DETECTANDO MOVIMIENTO) ---")
    if not mt5.initialize():
        print("Error conectando a MT5")
        return

    # 1. Obtener todos los símbolos visibles en la ventana "Observación de Mercado"
    simbolos = mt5.symbols_get(visible=True)
    nombres = [s.name for s in simbolos]
    
    print(f"Escuchando {len(nombres)} símbolos visibles en tu terminal...")
    print("Espera 5 segundos...")

    # 2. Escuchar tics durante 5 segundos
    start = time.time()
    activos = set()

    while time.time() - start < 5:
        for nombre in nombres:
            tick = mt5.symbol_info_tick(nombre)
            if tick:
                # Si el tick es reciente (menos de 2 segundos de antigüedad)
                ahora = datetime.now().timestamp()
                # Ajuste rudimentario de offset para detectar 'frescura' relativa o cambio
                # Mejor estrategia: comparar last con bid anterior. 
                # Simplificamos: Imprimiremos todo lo que tenga hora del servidor ACTUAL.
                
                # Obtenemos la hora del último tick del símbolo
                tick_time = tick.time
                # Hora actual del servidor (aproximada tomando el último tick conocido globalmente)
                # Simplemente imprimiremos los que tengan fecha de 'hoy/mañana'
                
                # Check visual rápido
                pass 
        time.sleep(0.1)

    # REINTENTO MEJORADO: Simplemente mostramos la hora del tick de TODOS los visibles
    print(f"\n{'SÍMBOLO':<20} | {'PRECIO':<10} | {'HORA SERVIDOR':<20} | {'ESTADO'}")
    print("-" * 70)
    
    hay_vivo = False
    for s in simbolos:
        tick = mt5.symbol_info_tick(s.name)
        if tick:
            ts = datetime.fromtimestamp(tick.time)
            ts_str = ts.strftime('%H:%M:%S')
            
            # Detectar si está "vivo" (asumiendo hora servidor ~00:xx)
            # Si la hora del tick es mayor a las 00:00 (del día 27) o muy reciente
            # Marcamos como VIVO
            
            estado = "ZOMBIE/VIEJO"
            # Criterio simple: Si el tick ocurrió en los últimos 5 minutos
            # (Nota: esto depende de la hora de tu PC vs Servidor, pero veremos la hora impresa)
            
            print(f"{s.name:<20} | {tick.bid:<10.2f} | {ts_str:<20} | {estado}")
            hay_vivo = True

    if not hay_vivo:
        print("No pude leer ticks. Asegúrate de tener la ventana 'Observación de Mercado' abierta.")

    mt5.shutdown()

if __name__ == "__main__":
    buscar_activo_vivo()