import polars as pl

class MicrostructureAnalyzer:
    def __init__(self):
        # No necesitamos estado previo por ahora, el análisis es ventana móvil
        pass

    def analizar_flujo(self, df_ticks: pl.DataFrame) -> dict:
        """
        Calcula la Presión de Ballenas detectando desplazamientos de liquidez.
        
        LÓGICA CORREGIDA (Whale Detector v2):
        - Solo contamos como COMPRA si el ASK se desplaza hacia ARRIBA (agresión compradora).
        - Solo contamos como VENTA si el BID se desplaza hacia ABAJO (agresión vendedora).
        - Ignoramos tics estáticos (ruido).
        """
        # 1. Validación de seguridad
        if df_ticks is None or df_ticks.height < 5:
            return {"status": "EMPTY", "desbalance": 0.0, "compras": 0, "ventas": 0, "intensidad": 0}

        try:
            # 2. Calcular Deltas (Cambios respecto al tick anterior)
            # Necesitamos ver cómo se movió el Bid y el Ask
            df_calc = df_ticks.with_columns([
                (pl.col("ask") - pl.col("ask").shift(1)).fill_null(0.0).alias("delta_ask"),
                (pl.col("bid") - pl.col("bid").shift(1)).fill_null(0.0).alias("delta_bid")
            ])
            
            # 3. Clasificar Agresividad (Filtrado Estricto)
            
            # COMPRAS: Alguien compró tanto que el Ask subió (> 0)
            # (Eliminamos el >= 0 que causaba el error de 'siempre verde')
            ticks_compra = df_calc.filter(pl.col("delta_ask") > 0).height
            
            # VENTAS: Alguien vendió tanto que el Bid bajó (< 0)
            ticks_venta = df_calc.filter(pl.col("delta_bid") < 0).height
            
            # Total de eventos RELEVANTES (excluyendo ruido estático)
            total_eventos = ticks_compra + ticks_venta
            
            # Si el mercado está muy quieto (solo ruido), devolvemos 0 neutral
            if total_eventos == 0:
                 return {
                    "status": "OK", 
                    "desbalance": 0.0, 
                    "intensidad": df_ticks.height, # Guardamos cuántos ticks totales vimos
                    "compras": 0, 
                    "ventas": 0
                }

            # 4. Calcular Desbalance Normalizado (-1.0 a 1.0)
            score = (ticks_compra - ticks_venta) / total_eventos
            
            return {
                "status": "OK",
                "desbalance": score,
                "intensidad": df_ticks.height,
                "compras": ticks_compra,
                "ventas": ticks_venta
            }
            
        except Exception as e:
            print(f"[MICRO ERROR] {e}")
            return {"status": "ERROR", "desbalance": 0.0, "compras": 0, "ventas": 0, "intensidad": 0}