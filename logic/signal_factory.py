import asyncio
import polars as pl
import time
from collections import deque

# --- CONFIGURACIÓN ---
SYMBOL = "BTCUSD" 
# UMBRAL: 0.20 es conservador. 
# Si quieres ver operaciones YA para probar, bájalo temporalmente a 0.05 o 0.08.
UMBRAL_BALLENA = 0.15  
HEARTBEAT_SEC = 30     # Latido cada 30s
COOLDOWN_SEC = 10      # Esperar 10s antes de repetir la misma señal

class SignalFactory:
    def __init__(self, executor):
        self.executor = executor
        self.running = True
        
        # --- MEMORIA (Estado Interno) ---
        self.ticks_buffer = pl.DataFrame()
        self.strategy_history = deque()
        
        # Para el Heartbeat y Anti-Spam
        self.last_heartbeat = time.time()
        self.processed_ticks = 0
        
        # Memoria de eventos para no repetir
        self.last_event_msg = None
        self.last_event_ts = 0

        # Variables para el Callback (Inyección de Dependencia)
        self.manager_callback = None
        self.manager_ref = None

    async def start_stream(self):
        """El Ojo que todo lo ve: Bucle infinito de análisis"""
        print(f"👁️ FACTORY: Escaneando {SYMBOL}...")
        print(f"   -> Umbral: {UMBRAL_BALLENA} | Anti-Spam: {COOLDOWN_SEC}s")
        
        while self.running:
            # 1. Obtener Tick
            tick = await self.executor.get_symbol_tick(SYMBOL)
            
            if tick:
                self.processed_ticks += 1
                
                # 2. Procesar (Devuelve tupla: Mensaje, Score)
                event_msg, score_val = self._process_tick(tick)
                
                # --- 3. LÓGICA DE SALIDA Y DISPARO ---
                if event_msg:
                    now = time.time()
                    
                    # Filtro Anti-Spam: 
                    # Solo actuamos si la señal cambió O si pasó el tiempo de espera
                    if (event_msg != self.last_event_msg) or (now - self.last_event_ts > COOLDOWN_SEC):
                        
                        # Separador visual si cambia la señal
                        if event_msg != self.last_event_msg:
                            print("\n" + "⚡"*30)
                        
                        print(f"🔔 DETECTADO: {event_msg}")
                        print(f"   Precio: {tick.bid:.2f} | Score: {score_val:.3f}")
                        print("-" * 40)
                        
                        # Actualizar memoria anti-spam
                        self.last_event_msg = event_msg
                        self.last_event_ts = now

                        # --- 🔥 DISPARAR EL MANAGER (EJECUCIÓN REAL) ---
                        if self.manager_callback and self.manager_ref:
                            # Llamamos a la función puente en main_v2
                            await self.manager_callback(event_msg, score_val, self.manager_ref)

            # 4. HEARTBEAT (Latido) - VERSIÓN LIMPIA
            current_time = time.time()
            if current_time - self.last_heartbeat > HEARTBEAT_SEC:
                price_disp = tick.bid if tick else "..."
                # Solo imprimimos si NO hay señal activa
                if time.time() - self.last_event_ts > COOLDOWN_SEC: 
                    # Usamos \r para sobreescribir la misma línea y no llenar la pantalla
                    print(f"💓 [VIVO] Tics Procesados: {self.processed_ticks} | Precio: {price_disp} | Esperando Ballenas...", end='\r')
                self.last_heartbeat = current_time

            # Pequeña pausa para ceder control al Event Loop
            await asyncio.sleep(0.01)

    def _process_tick(self, tick_obj):
        """
        Calcula matemáticas de flujo.
        Retorna: (Mensaje_String, Score_Float)
        Si no hay señal, retorna (None, 0.0)
        """
        if not tick_obj: return None, 0.0
        
        ts = int(time.time())
        tick = tick_obj._asdict()
        
        # A. Calcular Micro Score (Buffer Polars)
        row = pl.DataFrame({"ask": [tick['ask']], "bid": [tick['bid']]})
        
        try:
            self.ticks_buffer = pl.concat([self.ticks_buffer, row])
            # Mantener buffer optimizado (últimos 1000 ticks)
            if self.ticks_buffer.height > 1000: 
                self.ticks_buffer = self.ticks_buffer.tail(1000)
        except:
            self.ticks_buffer = row
            return None, 0.0

        if self.ticks_buffer.height < 10: return None, 0.0
        
        # Cálculo Delta (Numpy puro para velocidad extrema)
        df = self.ticks_buffer
        asks = df["ask"].to_numpy()
        bids = df["bid"].to_numpy()
        
        delta_ask = asks[1:] - asks[:-1]
        delta_bid = bids[1:] - bids[:-1]
        
        compras = (delta_ask > 0).sum()
        ventas = (delta_bid < 0).sum()
        total = compras + ventas
        
        micro_score = 0.0
        if total > 0:
            micro_score = (compras - ventas) / total

        # B. Detectar Estrategia (Ventana 5 min)
        self.strategy_history.append({'ts': ts, 'price': tick['bid'], 'score': micro_score})
        
        # Limpiar ventana de tiempo (300 seg)
        limit = ts - 300
        while self.strategy_history and self.strategy_history[0]['ts'] < limit:
            self.strategy_history.popleft()
            
        if len(self.strategy_history) < 20: return None, 0.0
        
        # Promedios
        avg_score = sum(d['score'] for d in self.strategy_history) / len(self.strategy_history)
        price_start = self.strategy_history[0]['price']
        price_end = self.strategy_history[-1]['price']
        delta_price = price_end - price_start
        
        # C. Retorno de Eventos
        
        # CASO 1: ABSORCION (Score Vendedor fuerte, pero Precio Sube/Aguanta)
        if avg_score < -UMBRAL_BALLENA and delta_price >= 0:
            msg = f"🛡️ ABSORCION_COMPRA (Vol: {avg_score:.2f} | Δ$: {delta_price:.2f})"
            return msg, avg_score
        
        # CASO 2: DISTRIBUCION (Score Comprador fuerte, pero Precio Baja/Aguanta)
        elif avg_score > UMBRAL_BALLENA and delta_price <= 0:
            msg = f"🧱 DISTRIBUCION_VENTA (Vol: {avg_score:.2f} | Δ$: {delta_price:.2f})"
            return msg, avg_score
        
        return None, 0.0