from collections import deque
import time

class WhaleDetector:
    def __init__(self, ventana_segundos=300):
        """
        ventana_segundos: Tiempo para el análisis acumulado (default 300s = 5 min).
        """
        self.ventana_segundos = ventana_segundos
        # Buffer: Lista de tuplas (timestamp, precio, score)
        self.history = deque()

    def detectar_estrategia(self, timestamp, micro_score, current_price):
        """
        Analiza la divergencia ACUMULADA en la ventana de tiempo.
        """
        # 1. Guardar foto del momento actual
        self.history.append({
            'ts': timestamp,
            'price': current_price,
            'score': micro_score
        })

        # 2. Limpiar datos viejos (Mantener solo la ventana deseada)
        limit_time = timestamp - self.ventana_segundos
        while self.history and self.history[0]['ts'] < limit_time:
            self.history.popleft()

        # Si no hay suficiente data (ej. primeros segundos), esperamos
        if len(self.history) < 10:
            return "RECOPILANDO_DATA", 0.0

        # 3. Calcular Acumulados
        # Precio Inicio vs Precio Fin
        price_start = self.history[0]['price']
        price_end = self.history[-1]['price']
        price_delta = price_end - price_start

        # Presión Promedio en el periodo (Sustained Pressure)
        # Sumamos todos los scores y dividimos. Nos dice la "intención promedio".
        avg_score = sum(d['score'] for d in self.history) / len(self.history)

        # UMBRALES (Ajustados para promedios, que suelen ser más suaves)
        UMBRAL_INTENSIDAD = 0.09 
        
        # --- LÓGICA DE DIVERGENCIA ACUMULADA ---

        # 1. ABSORCIÓN ALCISTA (Trampa de Osos Sostenida)
        # Promedio vendedor (-), pero precio subió o aguantó.
        if avg_score < -UMBRAL_INTENSIDAD and price_delta >= 0:
            return "ABSORCION_COMPRA", avg_score

        # 2. DISTRIBUCIÓN BAJISTA (Trampa de Toros Sostenida)
        # Promedio comprador (+), pero precio bajó o se estancó.
        elif avg_score > UMBRAL_INTENSIDAD and price_delta <= 0:
            return "DISTRIBUCION_VENTA", avg_score

        # --- LÓGICA DE CONVERGENCIA (Tendencia Sana) ---
        
        # 3. IMPULSO BAJISTA SANO
        elif avg_score < -UMBRAL_INTENSIDAD and price_delta < 0:
            return "IMPULSO_BAJISTA", avg_score

        # 4. IMPULSO ALCISTA SANO
        elif avg_score > UMBRAL_INTENSIDAD and price_delta > 0:
            return "IMPULSO_ALCISTA", avg_score

        return "RANGO_NEUTRAL", avg_score