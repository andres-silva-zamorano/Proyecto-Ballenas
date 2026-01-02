import asyncio
import MetaTrader5 as mt5
import sys
import os

# Asegurar que Python encuentre los módulos en la ruta
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.executor import AsyncExecutor
from core.risk_sentinel import RiskSentinel
from logic.signal_factory import SignalFactory
from logic.basket_manager import BasketManager

# --- PUENTE ENTRE FACTORY Y MANAGER ---
# Esta función conecta la detección (Factory) con la ejecución (Manager)
async def on_whale_signal(event_msg, score, manager):
    # event_msg viene como: "🐋 ABSORCION_COMPRA (Score: -0.35)"
    
    # Clasificación simple del string
    if "COMPRA" in event_msg:
        tipo = "ABSORCION_COMPRA"
    elif "VENTA" in event_msg:
        tipo = "DISTRIBUCION_VENTA"
    else:
        return

    # Delegar la decisión táctica al Manager
    await manager.process_signal(tipo, score)

async def main():
    print("\n" + "="*50)
    print("🚀 INICIANDO BALLENAS IA v3.0 (SMART EXIT ACTIVATED)")
    print("="*50)
    
    # 1. Inicializar MT5
    if not mt5.initialize():
        print(f"❌ Error Fatal: No se pudo iniciar MT5. {mt5.last_error()}")
        return

    # Configuración del Símbolo
    symbol = "BTCUSD" # Asegúrate que coincida con tu broker
    if not mt5.symbol_select(symbol, True):
        print(f"⚠️ Advertencia: No se pudo seleccionar {symbol}. Verifique el nombre.")

    # 2. Instancias de los Módulos
    executor = AsyncExecutor()
    sentinel = RiskSentinel(executor, max_daily_loss=500.0)
    manager = BasketManager(executor, symbol) # Ahora incluye lógica de Trailing Stop
    factory = SignalFactory(executor) 
    
    # 3. Inyección de Dependencias (Conectar cables)
    factory.manager_callback = on_whale_signal
    factory.manager_ref = manager
    
    # 4. Estado Inicial
    await sentinel.sync_initial_balance()
    
    print(f"\n✅ SISTEMA ARMADO PARA: {symbol}")
    print("   1. Sentinel (Riesgo Global): ACTIVO")
    print("   2. Factory (Detector Ticks): ACTIVO")
    print("   3. Manager (Gestión Salida): ACTIVO (Trailing Stop)")
    print("\n⚠️ [Ctrl + C] para detener el bot de forma segura.\n")
    
    # 5. LANZAR TAREAS CONCURRENTES (EL CEREBRO MULTITASKING)
    
    # Tarea A: Vigilancia de Riesgo (Sentinel)
    task_risk = asyncio.create_task(sentinel.monitor_pulse())
    
    # Tarea B: Vigilancia de Ganancias y Salida (Manager - NUEVO)
    # Esta tarea corre cada segundo para verificar si hay que cerrar por ganancia
    task_exit_brain = asyncio.create_task(manager.start_monitoring())
    
    # Tarea C: Detección de Señales (Factory)
    # Esta tarea corre a la velocidad de los ticks del mercado
    task_logic = asyncio.create_task(factory.start_stream())

    # 6. Bucle Principal (Esperar indefinidamente)
    try:
        # Gather mantiene vivas todas las tareas
        await asyncio.gather(task_risk, task_exit_brain, task_logic)
        
    except asyncio.CancelledError:
        print("\n🛑 Tareas del sistema detenidas.")
    except Exception as e:
        print(f"\n❌ Error crítico en el Loop Principal: {e}")
    finally:
        print("👋 Apagando conexión con MetaTrader 5...")
        mt5.shutdown()

if __name__ == "__main__":
    try:
        # Fix necesario para asyncio en Windows con subprocesos/sockets
        if os.name == 'nt':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        asyncio.run(main())
        
    except KeyboardInterrupt:
        print("\n👋 Bot detenido manualmente por el usuario.")
    except Exception as e:
        print(f"\n❌ Error inesperado al iniciar: {e}")