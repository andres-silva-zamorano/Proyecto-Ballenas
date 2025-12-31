import asyncio
import MetaTrader5 as mt5
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.executor import AsyncExecutor
from core.risk_sentinel import RiskSentinel
from logic.signal_factory import SignalFactory
from logic.basket_manager import BasketManager # <--- IMPORTAR NUEVO

# --- PUENTE ENTRE FACTORY Y MANAGER ---
# Esta función es el pegamento. Cuando Factory grita, esta función se ejecuta.
async def on_whale_signal(event_msg, score, manager):
    # event_msg es algo como "🐋 ABSORCION_COMPRA (Score: -0.35)"
    # Extraemos el tipo limpio
    if "COMPRA" in event_msg:
        tipo = "ABSORCION_COMPRA"
    elif "VENTA" in event_msg:
        tipo = "DISTRIBUCION_VENTA"
    else:
        return

    # Delegar al Manager
    await manager.process_signal(tipo, score)

async def main():
    print("\n" + "="*50)
    print("🚀 INICIANDO BALLENAS IA v2.2 (AUTO-TRADING ACTIVADO)")
    print("="*50)
    
    if not mt5.initialize():
        print("❌ Error MT5")
        return

    symbol = "BTCUSD" 
    mt5.symbol_select(symbol, True)

    # 1. Instancias
    executor = AsyncExecutor()
    sentinel = RiskSentinel(executor, max_daily_loss=500.0)
    manager = BasketManager(executor, symbol) # <--- INSTANCIA DEL MANAGER
    
    # 2. Configurar Factory con Callback
    # Ahora Factory necesita saber a quién avisar.
    # Modificaremos factory para que acepte un callback o lo hacemos en el loop aquí.
    # Para no tocar Factory de nuevo, usaremos el bucle de Factory y 
    # cuando retorne evento, llamamos al manager.
    
    factory = SignalFactory(executor) 
    
    # 3. Estado Inicial
    await sentinel.sync_initial_balance()
    print("\n✅ SISTEMA ARMADO: Sentinel + Factory + BasketManager.")
    print("⚠️ ADVERTENCIA: Este modo EJECUTARÁ ÓRDENES REALES (O Demo).")
    
    # 4. TAREAS
    task_risk = asyncio.create_task(sentinel.monitor_pulse())
    
    # Creamos una tarea envoltorio para conectar Factory -> Manager
    async def run_logic_pipeline():
        print(f"👁️ PIPELINE: Factory -> Manager escuchando en {symbol}...")
        while True:
            # Esperamos tick a tick dentro de factory... 
            # Como factory.start_stream() es un bucle infinito, necesitamos intervenirlo
            # O mejor, ejecutamos una versión modificada aquí mismo o editamos factory.
            
            # SOLUCIÓN LIMPIA: Ejecutamos el factory normal, pero modificamos SignalFactory
            # para aceptar un callback. 
            # PERO para no hacerte editar 3 archivos, usaremos polling en el factory modificado:
            
            # Hack rápido: SignalFactory ya imprime. 
            # Vamos a modificar LIGERA y FINALMENTE el start_stream de Factory para que retorne el evento
            # en lugar de solo imprimirlo? No, porque es async.
            
            # Lo correcto: Pasamos el manager al factory.
            # Como no quiero que edites factory de nuevo si no quieres, 
            # te daré la versión FINAL de SignalFactory abajo que llama al manager.
            pass

    # PARA QUE FUNCIONE TODO JUNTO, NECESITAMOS UN PEQUEÑO CAMBIO EN SIGNAL FACTORY
    # PARA QUE ACEPTE EL CALLBACK.
    
    # Vamos a inyectar el manager en el factory
    factory.manager_callback = on_whale_signal
    factory.manager_ref = manager
    
    # Lanzamos el stream (Nota: Necesitas actualizar SignalFactory con el código de abajo)
    task_logic = asyncio.create_task(factory.start_stream())

    try:
        await asyncio.gather(task_risk, task_logic)
    except asyncio.CancelledError:
        print("Apagando...")
    finally:
        mt5.shutdown()

if __name__ == "__main__":
    try:
        if os.name == 'nt':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except KeyboardInterrupt:
        pass