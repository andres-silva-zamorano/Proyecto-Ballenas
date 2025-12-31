import MetaTrader5 as mt5
import time

class MT5Trader:
    def __init__(self, symbol, lot_size=0.01, magic_number=999000):
        self.symbol = symbol
        self.lot = lot_size
        self.magic = magic_number
        self.verbose = True

    def enviar_orden(self, tipo_orden, precio_entrada, sl, tp, comentario="BallenasIA"):
        """
        Envía una orden al mercado con protección SL/TP.
        tipo_orden: 0 = COMPRA (ORDER_TYPE_BUY), 1 = VENTA (ORDER_TYPE_SELL)
        """
        # Asegurar conexión
        if not mt5.initialize():
            print("🔴 Error: No hay conexión con MT5 para operar.")
            return False

        # Rellenar estructura de la orden
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": self.lot,
            "type": tipo_orden,
            "price": precio_entrada,
            "sl": float(sl),
            "tp": float(tp),
            "deviation": 20, # Deslizamiento máximo permitido (puntos)
            "magic": self.magic,
            "comment": comentario,
            "type_time": mt5.ORDER_TIME_GTC, # Good Till Cancelled
            "type_filling": mt5.ORDER_FILLING_IOC, # O FOK, depende del broker
        }

        # Enviar
        result = mt5.order_send(request)
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"❌ ERROR EJECUCIÓN: {result.comment} (Código: {result.retcode})")
            return False
        else:
            tipo_txt = "COMPRA" if tipo_orden == mt5.ORDER_TYPE_BUY else "VENTA"
            print(f"✅ ORDEN EJECUTADA: {tipo_txt} @ {precio_entrada} | SL: {sl} | TP: {tp}")
            return True

    def cerrar_posiciones_existentes(self):
        """Cierra todas las posiciones abiertas por ESTE bot (Magic Number)"""
        positions = mt5.positions_get(symbol=self.symbol)
        if positions:
            for pos in positions:
                if pos.magic == self.magic:
                    # Crear orden opuesta para cerrar
                    tipo_cierre = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
                    precio_cierre = mt5.symbol_info_tick(self.symbol).bid if tipo_cierre == mt5.ORDER_TYPE_SELL else mt5.symbol_info_tick(self.symbol).ask
                    
                    req = {
                        "action": mt5.TRADE_ACTION_DEAL,
                        "symbol": self.symbol,
                        "volume": pos.volume,
                        "type": tipo_cierre,
                        "position": pos.ticket,
                        "price": precio_cierre,
                        "magic": self.magic,
                        "comment": "Cierre Auto",
                    }
                    mt5.order_send(req)
            print("🗑️ Posiciones anteriores cerradas.")
            
    def tengo_posicion_abierta(self):
        """Revisa si ya estamos dentro del mercado"""
        positions = mt5.positions_get(symbol=self.symbol)
        if positions:
            for pos in positions:
                if pos.magic == self.magic:
                    return True
        return False