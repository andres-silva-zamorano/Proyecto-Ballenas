import MetaTrader5 as mt5
import asyncio
import time

class BasketManager:
    def __init__(self, executor, symbol):
        self.executor = executor
        self.symbol = symbol
        self.lot_size = 0.01
        self.active_direction = None 
        
        # Control de Apilamiento
        self.last_trade_time = 0
        self.stack_cooldown = 60  # Esperar al menos 60s entre entradas adicionales
        self.max_positions = 5    # Máximo de balas en la recámara por tendencia

    async def process_signal(self, signal_type, score):
        """
        Lógica Táctica v2: Flip + Stacking (Apilamiento)
        """
        # 1. Mapear señal
        intencion = "BUY" if "COMPRA" in signal_type else "SELL"
        
        # 2. Verificar estado actual en MT5
        positions = await self.executor.get_positions()
        my_positions = [p for p in positions if p.symbol == self.symbol and p.magic == 555777]
        
        num_pos = len(my_positions)
        current_dir = None
        
        if num_pos > 0:
            # Asumimos dirección de la primera (canasta coherente)
            current_dir = "BUY" if my_positions[0].type == mt5.ORDER_TYPE_BUY else "SELL"

        print(f"⚡ MANAGER: Intención {intencion} (Score: {score:.2f}) | Posiciones Actuales: {num_pos} | Dir: {current_dir}")

        # 3. TÁCTICA DE COMBATE
        
        # A. ESCENARIO: Mercado Limpio -> Primera Entrada
        if num_pos == 0:
            print(f"✅ INICIO DE CICLO: Abriendo {intencion} inicial...")
            await self._open_trade(intencion)
            
        # B. ESCENARIO: Dirección Correcta -> ¿Apilamos?
        elif current_dir == intencion:
            now = time.time()
            # Condiciones para apilar:
            # 1. No hemos superado el máximo de posiciones.
            # 2. Ha pasado el tiempo de enfriamiento (para no entrar todo en el mismo precio).
            # 3. La señal sigue siendo fuerte (Score alto absoluto).
            
            if num_pos < self.max_positions and (now - self.last_trade_time > self.stack_cooldown):
                if abs(score) > 0.40: # Solo apilamos si la señal es fuerte (> 40%)
                    print(f"🚀 APILAMIENTO (STACK): Añadiendo posición {num_pos + 1}/{self.max_positions}...")
                    await self._open_trade(intencion)
                else:
                    print(f"ℹ️ MANTENER: Señal débil para apilar ({score:.2f}).")
            else:
                wait = int(self.stack_cooldown - (now - self.last_trade_time))
                wait_msg = f"Esperando {wait}s" if wait > 0 else "Max Posiciones"
                print(f"ℹ️ MANTENER: {wait_msg}.")
            
        # C. ESCENARIO: Giro de Mercado -> FLIP
        elif current_dir != intencion:
            print(f"🔄 FLIP: Cerrando {num_pos} posiciones de {current_dir} para ir a {intencion}...")
            await self._close_all(my_positions)
            await asyncio.sleep(1) # Pequeña pausa de seguridad
            await self._open_trade(intencion)

    async def _open_trade(self, direction):
        order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL
        
        res = await self.executor.execute_order(
            symbol=self.symbol,
            order_type=order_type,
            lots=self.lot_size,
            comment=f"Ballenas Stack"
        )
        
        if res:
            self.last_trade_time = time.time()
            print(f"   👉 Orden Ejecutada: Ticket #{res.order}")

    async def _close_all(self, positions):
        tasks = []
        for pos in positions:
            tasks.append(self.executor.close_position(pos.ticket))
        
        if tasks:
            await asyncio.gather(*tasks)
            print("   🗑️ Canasta liquidada.")