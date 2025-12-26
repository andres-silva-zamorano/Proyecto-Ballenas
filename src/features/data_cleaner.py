import polars as pl
import os
import sys

class DataCleaner:
    def __init__(self, input_filename="Dataset_Con_Regimenes.csv", output_filename="dataset_entrenamiento.parquet"):
        self.input_path = os.path.join("data", "raw", input_filename)
        self.output_path = os.path.join("data", "processed", output_filename)

    def ejecutar_limpieza(self):
        print(f"--- INICIANDO PROTOCOLO DE LIMPIEZA DE DATOS ---")
        print(f"[1] Buscando archivo raw: {self.input_path}")

        if not os.path.exists(self.input_path):
            print(f"ERROR: No se encuentra {self.input_path}")
            print("TIP: Copia tu archivo histórico de 15 meses en la carpeta 'data/raw/'")
            return False

        # Carga con inferencia de esquema para detectar tipos
        try:
            df = pl.read_csv(self.input_path, infer_schema_length=10000, ignore_errors=True)
        except Exception as e:
            print(f"ERROR LEYENDO CSV: {e}")
            return False

        rows_inicial = df.height
        print(f"    -> Registros cargados: {rows_inicial}")

        # [2] LIMPIEZA DE ESTRUCTURA
        print("[2] Optimizando estructura...")
        
        # A. Eliminar duplicados exactos (si hay timestamp)
        if "Timestamp" in df.columns:
            df = df.unique(subset=["Timestamp"], keep="first")
            # Intentar ordenar por fecha si es posible parsearla, si no, confiamos en el orden del CSV
            try:
                # Si es string fecha
                df = df.with_columns(pl.col("Timestamp").str.to_datetime(strict=False).alias("ts_temp"))
                df = df.sort("ts_temp").drop("ts_temp")
            except:
                pass # Si falla el ordenamiento por fecha, seguimos igual
        
        # B. Eliminar filas con Nulos en precios (Basura)
        cols_vitales = ["Close_Price", "EMA_Princ"]
        cols_presentes = [c for c in cols_vitales if c in df.columns]
        if cols_presentes:
            df = df.drop_nulls(subset=cols_presentes)

        # C. Conversión a Float32 (MANDAMIENTO DE RENDIMIENTO)
        # Las redes neuronales no necesitan precisión de 64 bits, y 32 bits usa la mitad de RAM.
        float_cols = [col for col in df.columns if df[col].dtype == pl.Float64]
        if float_cols:
            df = df.with_columns([
                pl.col(c).cast(pl.Float32) for c in float_cols
            ])

        # [3] REPORTE FINAL
        rows_final = df.height
        eliminados = rows_inicial - rows_final
        print(f"[3] Limpieza terminada.")
        print(f"    -> Filas eliminadas (Sucias/Dup): {eliminados}")
        print(f"    -> DATASET FINAL: {rows_final} registros listos.")

        # [4] GUARDADO ATÓMICO
        print(f"[4] Guardando binario (.parquet)...")
        try:
            os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
            df.write_parquet(self.output_path)
            print(f"    -> ÉXITO: Archivo guardado en {self.output_path}")
            return True
        except Exception as e:
            print(f"ERROR AL GUARDAR: {e}")
            return False

if __name__ == "__main__":
    # Puedes cambiar el nombre del archivo aquí si tu histórico se llama distinto
    cleaner = DataCleaner("Dataset_Con_Regimenes.csv") 
    cleaner.ejecutar_limpieza()