import polars as pl
import os
import sys

def verificar_probabilidades():
    path = os.path.join("data", "processed", "dataset_entrenamiento.parquet")
    
    if not os.path.exists(path):
        print("ERROR: No encuentro el archivo parquet.")
        return

    df = pl.read_parquet(path)
    print(f"--- INSPECCIÓN DE PROBABILIDADES ({df.height} filas) ---")

    # Lista de columnas de probabilidad
    cols_probs = [f"prob_regimen_{i}" for i in range(7)]
    
    # Verificar si existen
    missing = [c for c in cols_probs if c not in df.columns]
    if missing:
        print(f"ERROR: Faltan columnas: {missing}")
        return

    # Mostrar estadísticas para ver si están llenas o vacías
    print(f"{'COLUMNA':<20} | {'MAX (Valor más alto)':<20} | {'MEDIA':<20}")
    print("-" * 65)
    
    todo_cero = True
    for col in cols_probs:
        max_val = df[col].max()
        mean_val = df[col].mean()
        
        print(f"{col:<20} | {max_val:<20.4f} | {mean_val:<20.4f}")
        
        if max_val > 0:
            todo_cero = False

    print("-" * 65)
    if todo_cero:
        print("🔴 ALERTA ROJA: Todas las probabilidades son 0.0.")
        print("    Diagnóstico: El archivo histórico tiene la estructura, pero NO los cálculos.")
        print("    Solución: Debemos crear un script 'labeler.py' con tus reglas matemáticas para llenarlas.")
    else:
        print("🟢 LUZ VERDE: Detectamos probabilidades calculadas.")
        print("    Acción: Podemos entrenar la IA para que aprenda a predecirlas.")

if __name__ == "__main__":
    verificar_probabilidades()