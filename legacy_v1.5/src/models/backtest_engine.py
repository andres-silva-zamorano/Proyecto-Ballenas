import polars as pl
import numpy as np
import os

class BacktestEngine:
    def __init__(self, data_path, initial_capital=10000, spread_cost=1.0):
        self.data_path = data_path
        self.capital = initial_capital
        self.spread = spread_cost # Costo aproximado por trade en USD
        self.df = None

    def cargar_datos(self):
        if not os.path.exists(self.data_path):
            print("Error: No hay datos históricos.")
            return False
        
        # Leemos y limpiamos
        self.df = pl.read_csv(self.data_path, ignore_errors=True)
        
        # Asegurar tipos numéricos
        cols = ["Close_Price", "Micro_Score"]
        for c in cols:
            if c in self.df.columns:
                self.df = self.df.with_columns(pl.col(c).cast(pl.Float64))
        
        # Parsear fecha
        if "Timestamp" in self.df.columns:
            try:
                self.df = self.df.with_columns(pl.col("Timestamp").str.to_datetime(strict=False).alias("datetime"))
                self.df = self.df.sort("datetime")
            except: pass
            
        return True

    def ejecutar_simulacion(self, umbral_ballena=0.15, stop_loss_pct=0.005, take_profit_pct=0.015, timeframe_min=5):
        """
        Simula la estrategia de Absorción/Distribución
        """
        if self.df is None: return 0.0

        # 1. Agrupar datos según timeframe (Simular velas de 5m, 15m, etc)
        # Esto es vital: no operamos cada tick, operamos cierres de estructura
        df_sim = (
            self.df.sort("datetime")
            .group_by_dynamic("datetime", every=f"{timeframe_min}m")
            .agg([
                pl.col("Close_Price").first().alias("open"),
                pl.col("Close_Price").last().alias("close"),
                pl.col("Micro_Score").mean().alias("score_avg")
            ])
        ).with_columns([
            (pl.col("close") - pl.col("open")).alias("price_delta")
        ])

        balance = self.capital
        posicion = None # None, 'LONG', 'SHORT'
        precio_entrada = 0.0
        trades = []

        # Convertir a diccionarios para iterar rápido (Polars es rápido, pero para lógica de estados iteramos)
        rows = df_sim.to_dicts()

        for row in rows:
            precio = row['close']
            score = row['score_avg']
            delta = row['price_delta']
            
            if precio is None or score is None: continue

            # --- GESTIÓN DE SALIDA (SL/TP) ---
            if posicion == 'LONG':
                # Calcular PnL
                pnl = (precio - precio_entrada)
                pnl_pct = pnl / precio_entrada
                
                # Salida por TP o SL
                if pnl_pct >= take_profit_pct or pnl_pct <= -stop_loss_pct:
                    balance += pnl - self.spread
                    posicion = None
                    trades.append(pnl)
                    continue

            elif posicion == 'SHORT':
                pnl = (precio_entrada - precio)
                pnl_pct = pnl / precio_entrada
                
                if pnl_pct >= take_profit_pct or pnl_pct <= -stop_loss_pct:
                    balance += pnl - self.spread
                    posicion = None
                    trades.append(pnl)
                    continue

            # --- GESTIÓN DE ENTRADA (Lógica de Ballenas) ---
            if posicion is None:
                # ESTRATEGIA: ABSORCIÓN (Compra)
                # Score Rojo (< -umbral) + Precio Sube/Aguanta (delta >= 0)
                if score < -umbral_ballena and delta >= 0:
                    posicion = 'LONG'
                    precio_entrada = precio
                
                # ESTRATEGIA: DISTRIBUCIÓN (Venta)
                # Score Verde (> umbral) + Precio Baja/Aguanta (delta <= 0)
                elif score > umbral_ballena and delta <= 0:
                    posicion = 'SHORT'
                    precio_entrada = precio

        # Métricas Finales
        roi = ((balance - self.capital) / self.capital) * 100
        win_rate = 0
        if len(trades) > 0:
            wins = len([t for t in trades if t > 0])
            win_rate = (wins / len(trades)) * 100
            
        return {
            "balance_final": balance,
            "roi_pct": roi,
            "trades_total": len(trades),
            "win_rate": win_rate
        }

if __name__ == "__main__":
    # Prueba rápida
    path = os.path.join("data", "raw", "sesion_ballenas.csv")
    engine = BacktestEngine(path)
    if engine.cargar_datos():
        res = engine.ejecutar_simulacion()
        print(f"Resultado Simulación Base: {res}")