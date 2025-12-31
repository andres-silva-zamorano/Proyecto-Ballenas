import polars as pl
import numpy as np

class TickProcessor:
    def __init__(self):
        """
        Inicializa el procesador.
        No requiere estado interno persistente complejo para esta versión alpha,
        procesaremos ventanas deslizantes proporcionadas por el conector.
        """
        pass

    def procesar_flujo(self, df_ticks: pl.DataFrame) -> dict:
        """
        Ingesta un DataFrame de Tics (Bid/Ask) y calcula la presión neta.
        
        MANDAMIENTOS APLICADOS:
        - Uso estricto de Polars.
        - Solo Bid para ventas, Solo Ask para compras.
        - Sin Last, Sin Volumen.
        """
        if df_ticks.is_empty():
            return self._retorno_vacio()

        # 1. Calcular Deltas (Cambios precio a precio)
        # Usamos shift(1) para comparar fila actual con la anterior
        df_calc = df_ticks.with_columns([
            (pl.col("ask") - pl.col("ask").shift(1)).alias("delta_ask"),
            (pl.col("bid") - pl.col("bid").shift(1)).alias("delta_bid")
        ])

        # Filtrar la primera fila que será null por el shift
        df_calc = df_calc.drop_nulls()

        # 2. Lógica de "Manos Fuertes" (Whale Logic)
        # - Si Ask sube (>0): Alguien compró agresivamente barriendo la oferta.
        # - Si Bid baja (<0): Alguien vendió agresivamente rompiendo la demanda.
        # - Ignoramos cuando Ask baja o Bid sube (relleno de liquidez pasiva/ruido).
        
        compras_agresivas = df_calc.filter(pl.col("delta_ask") > 0).height
        ventas_agresivas = df_calc.filter(pl.col("delta_bid") < 0).height
        
        total_eventos = compras_agresivas + ventas_agresivas
        
        if total_eventos == 0:
            return self._retorno_vacio()

        # 3. Cálculo de Ratios
        ratio_compras = compras_agresivas / total_eventos
        ratio_ventas = ventas_agresivas / total_eventos
        
        # Desbalance: Rango -1 (Venta Pura) a +1 (Compra Pura)
        desbalance = ratio_compras - ratio_ventas

        # Intensidad: Cuántos ticks relevantes hubo vs el total de ticks analizados
        # Esto nos dice si el mercado está "rápido" o "lento"
        intensidad = total_eventos / df_ticks.height

        return {
            "status": "OK",
            "tick_count": df_ticks.height,
            "compras": compras_agresivas,
            "ventas": ventas_agresivas,
            "desbalance": desbalance, # La métrica CLAVE para el Flip
            "intensidad": intensidad
        }

    def _retorno_vacio(self):
        return {
            "status": "EMPTY",
            "tick_count": 0,
            "compras": 0,
            "ventas": 0,
            "desbalance": 0.0,
            "intensidad": 0.0
        }

    def obtener_regimen_actual(self, desbalance: float) -> str:
        """Helper para traducir el número a texto en la consola"""
        if desbalance > 0.3: return "ACUMULACIÓN (BULL)"
        if desbalance < -0.3: return "DISTRIBUCIÓN (BEAR)"
        return "RANGO / NEUTRAL"