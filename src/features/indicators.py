import polars as pl
import numpy as np

class TechnicalIndicators:
    def __init__(self):
        pass

    def calcular_features(self, df_velas: pl.DataFrame) -> dict:
        """
        Calcula indicadores técnicos avanzados para coincidir con Dataset_Con_Regimenes.csv
        """
        if df_velas.height < 300: # Necesitamos historial para estabilizar EMAs
            return {}

        # Clonamos para no afectar el original y ordenamos
        df = df_velas.clone()

        # --- 1. PREPARACIÓN DE PRECIOS ---
        df = df.with_columns([
            pl.col("close").shift(1).alias("prev_close"),
            (pl.col("high") - pl.col("low")).alias("tr1"),
            (pl.col("high") - pl.col("close").shift(1)).abs().alias("tr2"),
            (pl.col("low") - pl.col("close").shift(1)).abs().alias("tr3")
        ])

        # True Range (TR)
        df = df.with_columns(
            pl.max_horizontal(["tr1", "tr2", "tr3"]).alias("tr")
        )

        # --- 2. CÁLCULO DE EMAS (10 a 320) ---
        # EMA Principal (digamos 200) y otras
        periodos = [10, 20, 40, 80, 160, 320]
        exprs_ema = [pl.col("close").ewm_mean(span=p, adjust=False).alias(f"EMA_{p}") for p in periodos]
        df = df.with_columns(exprs_ema)
        
        # Definimos EMA Principal (ej. 80 para intradía o 200 macro)
        ema_princ_col = "EMA_80" 

        # --- 3. RSI (14 periodos) ---
        delta = df["close"].diff()
        
        # Separar ganancias y pérdidas
        # Nota: En Polars esto es más manual sin librerías externas
        up = delta.clip(lower_bound=0)
        down = delta.clip(upper_bound=0).abs()
        
        # Medias suavizadas (Wilder's Smoothing es similar a ewm alpha=1/14)
        roll_up = up.ewm_mean(span=27, adjust=False) # span=2n-1 aprox para Wilder
        roll_down = down.ewm_mean(span=27, adjust=False)
        
        rs = roll_up / roll_down
        rsi = 100.0 - (100.0 / (1.0 + rs))
        
        df = df.with_columns(rsi.alias("RSI_Val"))

        # --- 4. MACD (12, 26, 9) ---
        ema12 = df["close"].ewm_mean(span=12, adjust=False)
        ema26 = df["close"].ewm_mean(span=26, adjust=False)
        macd_line = ema12 - ema26
        # signal_line = macd_line.ewm_mean(span=9, adjust=False) # No se pide explícitamente en tabla pero es estándar
        
        df = df.with_columns(macd_line.alias("MACD_Val"))

        # --- 5. ATR (14) y RELATIVOS ---
        df = df.with_columns(
            pl.col("tr").ewm_mean(span=14, adjust=False).alias("ATR_Act")
        )
        # ATR Relativo (ATR / Precio)
        df = df.with_columns(
            (pl.col("ATR_Act") / pl.col("close") * 100).alias("ATR_Rel")
        )

        # --- 6. PENDIENTE (SLOPE) EMA PRINCIPAL ---
        # Angulo simple: cambio de la EMA en 1 vela
        df = df.with_columns(
            (pl.col(ema_princ_col) - pl.col(ema_princ_col).shift(1)).alias("EMA_Princ_Slope")
        )
        
        # --- 7. EXTRAER ÚLTIMA FILA (Valores actuales) ---
        last = df.tail(1)
        
        # Mapa exacto a columnas del CSV histórico
        features = {
            "Timestamp": str(last["timestamp"][0]),
            "ATR_Act": last["ATR_Act"][0],
            "ATR_Rel": last["ATR_Rel"][0],
            "EMA_Princ": last[ema_princ_col][0],
            "EMA_Princ_Slope": last["EMA_Princ_Slope"][0],
            "RSI_Val": last["RSI_Val"][0],
            "MACD_Val": last["MACD_Val"][0],
            # Placeholders para ADX/DI (complejo de calcular manual, simulamos 0 por ahora para mantener estructura)
            "ADX_Val": 0.0, 
            "DI_Plus": 0.0,
            "DI_Minus": 0.0,
            "ADX_Diff": 0.0,
            "RSI_Velocidad": 0.0, # Requiere diff del RSI anterior
            "Volumen_Relativo": 1.0, # Requiere media de volumen
            "Close_Price": last["close"][0]
        }
        
        # Agregar las EMAs individuales
        for p in periodos:
            features[f"EMA_{p}"] = last[f"EMA_{p}"][0]

        return features