import asyncio
import MetaTrader5 as mt5
from functools import partial

class AsyncExecutor:
    def __init__(self):
        self.loop = asyncio.get_running_loop()

    async def _run_in_thread(self, func, *args, **kwargs):
        return await self.loop.run_in_executor(None, partial(func, *args, **kwargs))

    async def get_account_info(self):
        return await self._run_in_thread(mt5.account_info)

    async def get_positions(self):
        positions = await self._run_in_thread(mt5.positions_get)
        return positions if positions else []

    async def get_symbol_tick(self, symbol):
        return await self._run_in_thread(mt5.symbol_info_tick, symbol)

    # --- FUNCIÓN ATÓMICA (TODO EN UNO) ---
    def _execute_atomic(self, symbol, order_type, lots, sl, tp, comment):
        """Esta función corre dentro del hilo para ser atómica"""
        
        # 1. Obtener precio FRESCO dentro del mismo hilo
        tick = mt5.symbol_info_tick(symbol)
        if not tick: return None
        
        price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid
        
        # 2. Detectar Modo Filling
        symbol_info = mt5.symbol_info(symbol)
        filling_mode = mt5.ORDER_FILLING_FOK # Default
        if symbol_info:
            modes = symbol_info.filling_mode
            if modes & 2: filling_mode = mt5.ORDER_FILLING_IOC
            elif modes & 1: filling_mode = mt5.ORDER_FILLING_FOK
            else: filling_mode = mt5.ORDER_FILLING_RETURN

        # 3. Construir Request
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(lots),
            "type": order_type,
            "price": price,
            "sl": float(sl),
            "tp": float(tp),
            "deviation": 100, # Aumentado a 100 para asegurar ejecución en test
            "magic": 555777,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling_mode,
        }

        # 4. Disparar
        return mt5.order_send(request)

    async def execute_order(self, symbol, order_type, lots, sl=0.0, tp=0.0, comment="BallenasIA"):
        """Wrapper asíncrono para la ejecución atómica"""
        result = await self._run_in_thread(
            self._execute_atomic, symbol, order_type, lots, sl, tp, comment
        )
        
        if result is None:
            print("❌ ERROR CRÍTICO: Fallo interno en _execute_atomic (tick vacío o error MT5).")
            return None

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"❌ RECHAZO DE ORDEN: {result.comment} (Código: {result.retcode})")
            return None
        
        return result

    async def close_position(self, ticket):
        def _close_sync(t):
            pos_tuple = mt5.positions_get(ticket=t)
            if not pos_tuple: return False
            pos = pos_tuple[0]
            
            symbol_info = mt5.symbol_info(pos.symbol)
            fill_mode = mt5.ORDER_FILLING_IOC
            if symbol_info and not (symbol_info.filling_mode & 2):
                fill_mode = mt5.ORDER_FILLING_FOK

            type_close = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
            tick = mt5.symbol_info_tick(pos.symbol)
            if not tick: return False
            price = tick.bid if type_close == mt5.ORDER_TYPE_SELL else tick.ask
            
            req = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": pos.symbol,
                "volume": pos.volume,
                "type": type_close,
                "position": t,
                "price": price,
                "magic": pos.magic,
                "comment": "Cierre Auto",
                "type_filling": fill_mode
            }
            return mt5.order_send(req)

        await asyncio.sleep(0.05) 
        return await self._run_in_thread(_close_sync, ticket)