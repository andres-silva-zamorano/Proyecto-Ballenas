import MetaTrader5 as mt5
import asyncio
import time
import sys

class BasketManager:
    def __init__(self, executor, symbol):
        self.executor = executor
        self.symbol = symbol
        self.lot_size = 0.01
        
        # Gestión
        self.active_direction = None 
        self.last_trade_time = 0
        self.stack_cooldown = 20 
        self.max_positions = 5
        self.stack_threshold = 0.25 
        
        # Salida Inteligente
        self.highest_profit = 0.0
        self.trailing_activated = False
        
        # Configuración
        self.activation_threshold = 5.0
        self.trailing_distance = 2.0
        self.hard_stop_loss = -20.0

    async def start_monitoring(self):
        print(f"🔔 MANAGER: Vigilancia PnL Activa...")
        while True:
            await self._check_status()
            await asyncio.sleep(1)

    async def _check_status(self):
        positions = await self.executor.get_positions()
        my_positions = [p for p in positions if p.symbol == self.symbol and p.magic == 555777]
        
        if not my_positions:
            self.highest_profit = 0.0
            self.trailing_activated = False
            return

        # Calcular PnL
        current_profit = sum([p.profit for p in my_positions]) + sum([p.swap for p in my_positions])
        num_pos = len(my_positions)
        dir_str = "BUY" if my_positions[0].type == mt5.ORDER_TYPE_BUY else "SELL"
        
        # Actualizar Pico
        if current_profit > self.highest_profit:
            self.highest_profit = current_profit

        # --- REPORTE VISUAL CADA 5 SEGUNDOS (Para no saturar) ---
        if int(time.time()) % 5 == 0:
            # Borramos línea actual para imprimir estado limpio
            print(" " * 100, end='\r')
            trail_status = "🔒 ACTIVO" if self.trailing_activated else "⏳ ESPERA"
            print(f"💼 CARTERA: {num_pos}x {dir_str} | PnL: ${current_profit:.2f} | Pico: ${self.highest_profit:.2f} | Trailing: {trail_status}")

        # --- LÓGICA DE SALIDA ---
        
        # A. Stop Loss Global
        if current_profit <= self.hard_stop_loss:
            print(f"\n💀 STOP LOSS GLOBAL: ${current_profit:.2f}. CERRANDO.")
            await self._close_all(my_positions)
            return

        # B. Trailing Stop
        if current_profit >= self.activation_threshold:
            self.trailing_activated = True
        
        if self.trailing_activated:
            floor = self.highest_profit - self.trailing_distance
            if current_profit < floor:
                print(f"\n💰 TAKE PROFIT: Ganancia ${current_profit:.2f} (Retroceso desde ${self.highest_profit:.2f}).")
                await self._close_all(my_positions)

    async def process_signal(self, signal_type, score):
        # Lógica de entrada idéntica a la anterior...
        intencion = "BUY" if "COMPRA" in signal_type else "SELL"
        positions = await self.executor.get_positions()
        my_positions = [p for p in positions if p.symbol == self.symbol and p.magic == 555777]
        num_pos = len(my_positions)
        current_dir = None
        if num_pos > 0:
            current_dir = "BUY" if my_positions[0].type == mt5.ORDER_TYPE_BUY else "SELL"

        # Borrar línea de heartbeat para que el log de evento se vea bien
        print(" " * 100, end='\r')

        if num_pos == 0:
            print(f"✅ INICIO: Abriendo {intencion} (Score: {score:.2f})...")
            await self._open_trade(intencion)
            
        elif current_dir == intencion:
            now = time.time()
            if num_pos < self.max_positions and (now - self.last_trade_time > self.stack_cooldown):
                if abs(score) > self.stack_threshold:
                    print(f"🚀 APILANDO: +1 {intencion} (Total: {num_pos+1})")
                    await self._open_trade(intencion)
                else:
                    # Opcional: Imprimir log de mantenimiento solo si quieres mucho detalle
                    # print(f"ℹ️ MANTENER: Señal presente pero suave.")
                    pass
            
        elif current_dir != intencion:
            if abs(score) > 0.20:
                print(f"🔄 FLIP: Cerrando {current_dir} -> Abriendo {intencion}...")
                await self._close_all(my_positions)
                await asyncio.sleep(1)
                await self._open_trade(intencion)

    async def _open_trade(self, direction):
        order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL
        res = await self.executor.execute_order(self.symbol, order_type, self.lot_size, comment="Ballenas v3.1")
        if res:
            self.last_trade_time = time.time()
            print(f"   👉 Orden #{res.order} enviada.")

    async def _close_all(self, positions):
        tasks = []
        for pos in positions:
            tasks.append(self.executor.close_position(pos.ticket))
        if tasks:
            await asyncio.gather(*tasks)
            print("   🗑️ Posiciones cerradas.")
            self.highest_profit = 0.0
            self.trailing_activated = False