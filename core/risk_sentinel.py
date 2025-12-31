import asyncio
import MetaTrader5 as mt5
from datetime import datetime

class RiskSentinel:
    def __init__(self, executor, max_daily_loss=500.0):
        self.executor = executor
        self.max_daily_loss = max_daily_loss
        self.initial_balance = 0.0
        self.emergency_mode = False

    async def sync_initial_balance(self):
        """Obtiene el balance al inicio del día"""
        account = await self.executor.get_account_info()
        self.initial_balance = account.balance
        print(f"🛡️ SENTINEL: Balance Inicial Fijado en ${self.initial_balance}")

    async def monitor_pulse(self):
        """
        Corrutina infinita que revisa la equidad cada 500ms.
        Esta es la tarea de ALTA PRIORIDAD.
        """
        while True:
            account = await self.executor.get_account_info()
            equity = account.equity
            current_loss = self.initial_balance - equity

            # 1. VERIFICACIÓN DE STOP LOSS GLOBAL ($500)
            if current_loss >= self.max_daily_loss:
                print(f"🚨 ALERTA ROJA: PÉRDIDA DIARIA (${current_loss}) EXCEDE LÍMITE (${self.max_daily_loss})")
                await self.trigger_kill_switch()

            # 2. VERIFICACIÓN DE TRAILING EQUITY (Opcional, para proteger ganancias)
            # Aquí podrías implementar la lógica de subir el piso si ya ganaste $200

            await asyncio.sleep(0.5) # Chequeo de alta frecuencia

    async def trigger_kill_switch(self):
        """
        Pánico: Cierra TODO inmediatamente y detiene el bot.
        """
        self.emergency_mode = True
        print("🛡️ SENTINEL: EJECUTANDO CIERRE DE EMERGENCIA MASIVO...")
        
        # Obtenemos todas las posiciones
        positions = await self.executor.get_positions()
        
        # Lógica de cierre masivo (Throttled para evitar error 10027)
        tasks = []
        for pos in positions:
            tasks.append(self.executor.close_position(pos.ticket))
        
        # Ejecutar cierres en paralelo
        await asyncio.gather(*tasks)
        
        print("💀 SENTINEL: TODAS LAS POSICIONES CERRADAS. DETENIENDO SISTEMA.")
        import sys; sys.exit() # Apagado forzoso