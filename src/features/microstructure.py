import polars as pl

class MicrostructureAnalyzer:
    def __init__(self):
        # No necesitamos estado previo por ahora, el análisis es ventana móvil
        pass

    def analizar_flujo(self, df_ticks: pl.DataFrame) -> dict:
        """
        Calcula el desbalance de compradores vs vendedores en los últimos N tics.
        Retorna:
          - status: "OK" o "EMPTY"
          - desbalance: float (-1.0 (venta extrema) a 1.0 (compra extrema))
          - intensidad: int (total de tics analizados)
          - compras: int (volumen estimado de ask)
          - ventas: int (volumen estimado de bid)
        """
        # Validación básica de datos
        if df_ticks is None or df_ticks.height < 10:
            return {"status": "EMPTY", "desbalance": 0.0, "compras": 0, "ventas": 0, "intensidad": 0}

        # --- LÓGICA DE PRESIÓN (TICK AGGRESSION) ---
        # Determinamos si un tic fue "compra agresiva" (golpeó el Ask) o "venta agresiva" (golpeó el Bid).
        # Usamos el cambio de precio del 'bid' como proxy simple:
        # - Si el bid sube o se mantiene, asumimos presión de compra que sostiene el precio.
        # - Si el bid baja, asumimos presión de venta que empuja el precio.
        
        # 1. Calcular el delta (cambio) del precio bid respecto al tic anterior
        try:
            df_calc = df_ticks.with_columns(
                (pl.col("bid") - pl.col("bid").shift(1)).fill_null(0.0).alias("delta_bid")
            )
            
            # 2. Clasificar tics
            # Compras: Tics donde el bid NO bajó (delta >= 0)
            ticks_compra = df_calc.filter(pl.col("delta_bid") >= 0).height
            # Ventas: Tics donde el bid SÍ bajó (delta < 0)
            ticks_venta = df_calc.filter(pl.col("delta_bid") < 0).height
            
            total_ticks = ticks_compra + ticks_venta
            
            if total_ticks == 0:
                 return {"status": "EMPTY", "desbalance": 0.0}

            # 3. Calcular Desbalance (Score de -1 a 1)
            # Fórmula: (Compras - Ventas) / Total
            score = (ticks_compra - ticks_venta) / total_ticks
            
            return {
                "status": "OK",
                "desbalance": score,
                "intensidad": total_ticks,
                "compras": ticks_compra,
                "ventas": ticks_venta
            }
            
        except Exception as e:
            print(f"[MICRO ERROR] {e}")
            return {"status": "ERROR", "desbalance": 0.0}