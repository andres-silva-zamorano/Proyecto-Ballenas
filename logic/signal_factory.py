import asyncio
import polars as pl
import time
import sys
from collections import deque

# --- CONFIGURACIÓN ---
SYMBOL = "BTCUSD" 
UMBRAL_BALLENA = 0.07  # Tu umbral actual
HEARTBEAT_SEC = 1      # Actualización visual cada segundo (Dashboard style)
COOLDOWN_SEC = 10      

class SignalFactory:
    def __init__(self, executor):
        self.executor = executor
        self.running = True
        
        # Estado
        self.ticks_buffer = pl.DataFrame()
        self.strategy_history = deque()
        self.last_heartbeat = time.time()
        self.processed_ticks = 0
        
        # Memoria eventos
        self.last_event_msg = None
        self.last_event_ts = 0
        
        # Callbacks
        self.manager_callback = None
        self.manager_ref = None
        
        # Info visual
        self.current_score = 0.0

    async def start_stream(self):
        print(f"👁️ FACTORY: Radar Activo en {SYMBOL}...")
        print(f"   -> Umbral Disparo: {UMBRAL_BALLENA}")
        
        while self.running:
            tick = await self.executor.get_symbol_tick(SYMBOL)
            
            if tick:
                self.processed_ticks += 1
                msg, score = self._process_tick(tick)
                self.current_score = score # Guardamos para visualizar
                
                # --- DISPARO DE SEÑAL ---
                if msg:
                    now = time.time()
                    if (msg != self.last_event_msg) or (now - self.last_event_ts > COOLDOWN_SEC):
                        # Limpiamos la línea actual antes de imprimir el evento
                        print(" " * 100, end='\r') 
                        
                        if msg != self.last_event_msg: print("\n" + "⚡"*30)
                        
                        print(f"🔔 DETECTADO: {msg}")
                        print(f"   Precio: {tick.bid:.2f} | Score: {score:.3f}")
                        print("-" * 40)
                        
                        self.last_event_msg = msg
                        self.last_event_ts = now

                        if self.manager_callback and self.manager_ref:
                            await self.manager_callback(msg, score, self.manager_ref)

            # --- DASHBOARD VISUAL (HEARTBEAT) ---
            current_time = time.time()
            if current_time - self.last_heartbeat > HEARTBEAT_SEC:
                # Solo pintamos si no estamos en medio de una señal activa (para no ensuciar)
                if time.time() - self.last_event_ts > COOLDOWN_SEC:
                    self._print_dashboard(tick)
                self.last_heartbeat = current_time

            await asyncio.sleep(0.01)

    def _print_dashboard(self, tick):
        """Imprime una línea de estado que se sobrescribe a sí misma"""
        price = tick.bid if tick else 0.0
        
        # Termómetro visual del Score
        score_pct = self.current_score * 100
        bar_len = 10
        filled = int(abs(self.current_score) / UMBRAL_BALLENA * bar_len)
        filled = min(filled, bar_len)
        
        bar = "▒" * filled + "░" * (bar_len - filled)
        direction = "🟢 BULL" if self.current_score < 0 else "🔴 BEAR" if self.current_score > 0 else "⚪ NEUT"
        
        # Colorama sería ideal, pero usaremos texto simple para compatibilidad
        status_line = (
            f"\r💓 Tics: {self.processed_ticks} | "
            f"Precio: {price:.2f} | "
            f"Presión: {self.current_score:+.3f} [{bar}] {direction}    "
        )
        
        sys.stdout.write(status_line)
        sys.stdout.flush()

    def _process_tick(self, tick_obj):
        if not tick_obj: return None, 0.0
        
        ts = int(time.time())
        tick = tick_obj._asdict()
        
        # Acumulación optimizada
        row = pl.DataFrame({"ask": [tick['ask']], "bid": [tick['bid']]})
        try:
            self.ticks_buffer = pl.concat([self.ticks_buffer, row])
            if self.ticks_buffer.height > 1000: self.ticks_buffer = self.ticks_buffer.tail(1000)
        except:
            self.ticks_buffer = row
            return None, 0.0

        if self.ticks_buffer.height < 10: return None, 0.0
        
        # Cálculo Score
        df = self.ticks_buffer
        asks = df["ask"].to_numpy()
        bids = df["bid"].to_numpy()
        delta_ask = asks[1:] - asks[:-1]
        delta_bid = bids[1:] - bids[:-1]
        compras = (delta_ask > 0).sum()
        ventas = (delta_bid < 0).sum()
        total = compras + ventas
        
        micro_score = 0.0
        if total > 0: micro_score = (compras - ventas) / total

        # Estrategia
        self.strategy_history.append({'ts': ts, 'price': tick['bid'], 'score': micro_score})
        limit = ts - 300
        while self.strategy_history and self.strategy_history[0]['ts'] < limit:
            self.strategy_history.popleft()
            
        if len(self.strategy_history) < 20: return None, 0.0
        
        avg_score = sum(d['score'] for d in self.strategy_history) / len(self.strategy_history)
        price_start = self.strategy_history[0]['price']
        price_end = self.strategy_history[-1]['price']
        delta_price = price_end - price_start
        
        # Detección
        if avg_score < -UMBRAL_BALLENA and delta_price >= 0:
            return f"🛡️ ABSORCION_COMPRA (Vol: {avg_score:.2f} | Δ$: {delta_price:.2f})", avg_score
        elif avg_score > UMBRAL_BALLENA and delta_price <= 0:
            return f"🧱 DISTRIBUCION_VENTA (Vol: {avg_score:.2f} | Δ$: {delta_price:.2f})", avg_score
        
        return None, avg_score