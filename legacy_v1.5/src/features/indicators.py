import polars as pl
import numpy as np

class TechnicalIndicators:
    def __init__(self):
        pass

    def calcular_features(self, df_velas: pl.DataFrame) -> dict:
        """
        Calcula indicadores técnicos usando EXCLUSIVAMENTE Polars.
        Salida: Diccionario con los valores de la última vela listos para la IA.
        """
        # Validación de seguridad
        if df_velas is None or df_velas.height < 300:
            return {}

        # Clonamos para no afectar el dataframe original del monitor
        df = df_velas.clone()

        # Parámetros (Alineados con tu entrenamiento)
        RSI_PERIOD = 14
        ATR_PERIOD = 14
        ADX_PERIOD = 14
        EMA_PRINCIPAL = 80  # Según tu predictor

        # --- 1. PRE-CÁLCULOS (TR, Deltas) ---
        df = df.with_columns([
            pl.col("close").cast(pl.Float64),
            pl.col("high").cast(pl.Float64),
            pl.col("low").cast(pl.Float64),
            pl.col("tick_volume").cast(pl.Float64),
            pl.col("close").shift(1).alias("prev_close")
        ])

        # True Range
        df = df.with_columns([
            (pl.col("high") - pl.col("low")).alias("tr0"),
            (pl.col("high") - pl.col("prev_close")).abs().alias("tr1"),
            (pl.col("low") - pl.col("prev_close")).abs().alias("tr2"),
        ]).with_columns(
            pl.max_horizontal(["tr0", "tr1", "tr2"]).alias("TR")
        )

        # --- 2. INDICADORES BÁSICOS (EMA, ATR, Vol Relativo) ---
        df = df.with_columns([
            pl.col("close").ewm_mean(span=EMA_PRINCIPAL, adjust=False).alias("EMA_Princ"),
            pl.col("TR").ewm_mean(span=ATR_PERIOD, adjust=False).alias("ATR_Act"),
            pl.col("tick_volume").rolling_mean(window_size=20).alias("vol_ma")
        ])

        # Derivados Básicos
        df = df.with_columns([
            (pl.col("ATR_Act") / pl.col("close")).alias("ATR_Rel"),
            (pl.col("tick_volume") / pl.col("vol_ma")).fill_nan(0).alias("Volumen_Relativo"),
            (pl.col("EMA_Princ") - pl.col("EMA_Princ").shift(1)).alias("EMA_Princ_Slope")
        ])

        # --- 3. RSI (Calculado en Polars nativo) ---
        # Delta
        df = df.with_columns((pl.col("close") - pl.col("prev_close")).alias("delta"))
        
        # Up/Down moves
        df = df.with_columns([
            pl.when(pl.col("delta") > 0).then(pl.col("delta")).otherwise(0).alias("gain"),
            pl.when(pl.col("delta") < 0).then(pl.col("delta").abs()).otherwise(0).alias("loss")
        ])

        # Medias suavizadas (RMA / Wilder's SMMA es similar a ewm con span=2N-1)
        # Para RSI 14, span ≈ 27
        df = df.with_columns([
            pl.col("gain").ewm_mean(span=27, adjust=False).alias("avg_gain"),
            pl.col("loss").ewm_mean(span=27, adjust=False).alias("avg_loss")
        ])

        # RS y RSI final
        df = df.with_columns([
            (pl.col("avg_gain") / pl.col("avg_loss")).alias("rs")
        ]).with_columns(
            (100 - (100 / (1 + pl.col("rs")))).fill_nan(50).alias("RSI_Val")
        )

        # --- 4. MACD (12, 26, 9) ---
        df = df.with_columns([
            pl.col("close").ewm_mean(span=12, adjust=False).alias("ema12"),
            pl.col("close").ewm_mean(span=26, adjust=False).alias("ema26")
        ]).with_columns(
            (pl.col("ema12") - pl.col("ema26")).alias("MACD_Val")
        )

        # --- 5. ADX (El que faltaba) ---
        df = df.with_columns([
            (pl.col("high") - pl.col("high").shift(1)).alias("up_move"),
            (pl.col("low").shift(1) - pl.col("low")).alias("down_move")
        ])

        # Directional Movement (+DM, -DM)
        df = df.with_columns([
            pl.when((pl.col("up_move") > pl.col("down_move")) & (pl.col("up_move") > 0))
              .then(pl.col("up_move")).otherwise(0).alias("plus_dm"),
            pl.when((pl.col("down_move") > pl.col("up_move")) & (pl.col("down_move") > 0))
              .then(pl.col("down_move")).otherwise(0).alias("minus_dm")
        ])

        # Smooth DM y TR
        df = df.with_columns([
            pl.col("plus_dm").ewm_mean(span=ADX_PERIOD, adjust=False).alias("smooth_plus"),
            pl.col("minus_dm").ewm_mean(span=ADX_PERIOD, adjust=False).alias("smooth_minus"),
            pl.col("TR").ewm_mean(span=ADX_PERIOD, adjust=False).alias("smooth_tr")
        ])

        # DI+ y DI-
        df = df.with_columns([
            (100 * pl.col("smooth_plus") / pl.col("smooth_tr")).alias("plus_di"),
            (100 * pl.col("smooth_minus") / pl.col("smooth_tr")).alias("minus_di")
        ])

        # DX y ADX
        df = df.with_columns(
            (100 * (pl.col("plus_di") - pl.col("minus_di")).abs() / 
             (pl.col("plus_di") + pl.col("minus_di"))).fill_nan(0).alias("dx")
        ).with_columns(
            pl.col("dx").ewm_mean(span=ADX_PERIOD, adjust=False).alias("ADX_Val")
        )

        # --- 6. EXTRACCIÓN FINAL ---
        # Tomamos la última fila válida
        last_row = df.tail(1).to_dicts()[0]

        # Retornamos SOLO lo que pide el Predictor + Datos para el CSV
        features_dict = {
            # Datos básicos
            "Timestamp": str(last_row["timestamp"]),
            "Close_Price": last_row["close"],
            
            # Features para la IA (Deben coincidir con predictor.py)
            "ATR_Rel": last_row["ATR_Rel"],
            "RSI_Val": last_row["RSI_Val"],
            "MACD_Val": last_row["MACD_Val"],
            "ADX_Val": last_row["ADX_Val"],
            "EMA_Princ_Slope": last_row["EMA_Princ_Slope"],
            "Volumen_Relativo": last_row["Volumen_Relativo"],
            
            # Extras visuales
            "EMA_Princ": last_row["EMA_Princ"],
            "ATR_Act": last_row["ATR_Act"]
        }

        return features_dict