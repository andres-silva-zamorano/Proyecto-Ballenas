import polars as pl
import os
import sys

# Rutas
INPUT_FILE = os.path.join("data", "raw", "Dataset_Con_Regimenes.csv")
OUTPUT_FILE = os.path.join("data", "raw", "historial_completo.csv")

def reciclar_dataset_polars():
    print(f"--- ♻️ RECICLANDO DATASET HISTÓRICO (MOTOR POLARS) ---")
    
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Error: No encuentro {INPUT_FILE}")
        return

    # 1. Cargar Datos con Polars (Lazy es más eficiente pero Eager está bien aquí)
    print("⏳ Leyendo archivo histórico...")
    try:
        # ignore_errors=True ayuda si hay alguna línea corrupta
        df = pl.read_csv(INPUT_FILE, ignore_errors=True)
    except Exception as e:
        print(f"❌ Error leyendo CSV: {e}")
        return

    print(f"✅ Cargadas {df.height} filas.")

    # 2. Conversiones y Limpieza
    print("⚙️ Procesando fechas y columnas...")
    
    # Preparamos las expresiones para ejecutar todo de una vez (Query Optimization)
    q = (
        df.lazy()
        # A. Normalizar Fechas: Formato YYYY.MM.DD HH:MM
        .with_columns(
            pl.col("Timestamp")
            .str.to_datetime(format="%Y.%m.%d %H:%M", strict=False)
            .alias("datetime")
        )
        # Filtrar fechas que no se pudieron leer
        .drop_nulls(subset=["datetime"])
        .sort("datetime")
        
        # B. Renombrar Timestamp para que coincida con el sistema nuevo
        .drop("Timestamp") 
        .rename({"datetime": "Timestamp"})

        # C. Asegurar tipos numéricos (Float64 para precisión)
        .with_columns([
            pl.col("Close_Price").cast(pl.Float64),
            pl.col("ATR_Act").cast(pl.Float64),
            pl.col("Volumen_Relativo").cast(pl.Float64)
        ])
    )

    # 3. CÁLCULO VECTORIZADO DEL MICRO SCORE (Formula Proxy)
    print("⚙️ Calculando huella de ballenas (Vectorizado)...")
    
    q = q.with_columns([
        # Cambio de precio (Diff)
        (pl.col("Close_Price") - pl.col("Close_Price").shift(1)).alias("price_change")
    ]).with_columns([
        # Evitar división por cero en ATR
        pl.when(pl.col("ATR_Act") == 0).then(0.00001).otherwise(pl.col("ATR_Act")).alias("atr_safe")
    ]).with_columns([
        # Force: ¿Cuántos ATRs se movió el precio?
        (pl.col("price_change") / pl.col("atr_safe")).alias("force"),
        
        # Rellenar Volumen Relativo nulo con 1.0 (Neutral)
        pl.col("Volumen_Relativo").fill_null(1.0).alias("vol_rel")
    ]).with_columns([
        # FÓRMULA FINAL: Fuerza * Volumen
        (pl.col("force") * pl.col("vol_rel")).alias("raw_score")
    ]).with_columns([
        # Normalización y Clip (-1 a 1)
        # Dividimos por 3.0 para suavizar picos extremos
        (pl.col("raw_score") / 3.0).clip(-1.0, 1.0).alias("Micro_Score")
    ])

    # 4. Selección Final y Ejecución
    print("💾 Guardando resultado...")
    
    # Seleccionamos solo lo que necesita Optuna
    df_final = (
        q.select([
            pl.col("Timestamp"),
            pl.col("Close_Price"),
            pl.col("Micro_Score")
        ])
        .drop_nulls() # Eliminar la primera fila que tiene Null por el shift
        .collect()    # ¡AQUÍ SE EJECUTA TODO!
    )
    
    # Guardar a CSV
    df_final.write_csv(OUTPUT_FILE)
    
    print(f"💾 Archivo GENERADO: {OUTPUT_FILE}")
    print(f"📊 {df_final.height} velas procesadas a la velocidad del rayo.")
    print("👉 Próximo paso: 'python src/models/optimize_strategy.py'")

if __name__ == "__main__":
    reciclar_dataset_polars()