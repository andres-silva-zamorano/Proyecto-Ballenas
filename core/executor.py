import asyncio
import MetaTrader5 as mt5
from functools import partial

class AsyncExecutor:
    def __init__(self):
        self.loop = asyncio.get_running_loop()

    async def _run_in_thread(self, func, *args, **kwargs):
        """Ejecuta en hilo separado para no bloquear el Loop"""
        return await self.loop.run_in_executor(None, partial(func, *args, **kwargs))

    async def get_account_info(self):
        return await self._run_in_thread(mt5.account_info)

    async def get_positions(self):
        positions = await self._run_in_thread(mt5.positions_get)
        return positions if positions else []

    async def get_symbol_tick(self, symbol):
        return await self._run_in_thread(mt5.symbol_info_tick, symbol)

    async def execute_order(self, symbol, order_type, lots, sl=0.0, tp=0.0, comment="BallenasIA"):
        """Envía una orden al mercado de forma asíncrona y SEGURA"""
        
        # 1. Obtener precio actual
        tick = await self.get_symbol_tick(symbol)
        if not tick: 
            print("❌ ERROR EXECUTOR: No se pudo obtener tick para operar.")
            return None
        
        price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid
        
        # 2. Construir Request
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(lots),
            "type": order_type,
            "price": price,
            "sl": float(sl),
            "tp": float(tp),
            "deviation": 20,
            "magic": 555777,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        # 3. Enviar Orden (Con protección contra None)
        result = await self._run_in_thread(mt5.order_send, request)
        
        # --- CORRECCIÓN CRÍTICA AQUÍ ---
        if result is None:
            print("❌ ERROR CRÍTICO MT5: 'order_send' devolvió None. Verifique conexión o parámetros.")
            # Tip: A veces pasa si el lotaje es inválido para el símbolo
            return None

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"❌ RECHAZO DE ORDEN: {result.comment} (Código: {result.retcode})")
            return None
        
        return result

    async def close_position(self, ticket):
        """Cierra una posición específica"""
        def _close_sync(t):
            pos_tuple = mt5.positions_get(ticket=t)
            if not pos_tuple: return False
            pos = pos_tuple[0]
            
            # Lógica inversa para cerrar
            type_close = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
            
            # Obtener precio fresco síncrono (dentro del hilo)
            tick_info = mt5.symbol_info_tick(pos.symbol)
            if not tick_info: return False
            
            price_close = tick_info.bid if type_close == mt5.ORDER_TYPE_SELL else tick_info.ask
            
            req = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": pos.symbol,
                "volume": pos.volume,
                "type": type_close,
                "position": t,
                "price": price_close,
                "magic": pos.magic,
                "comment": "Cierre Auto"
            }
            return mt5.order_send(req)

        # THROTTLING: Pausa de 50ms para evitar error 10027
        await asyncio.sleep(0.05) 
        return await self._run_in_thread(_close_sync, ticket)