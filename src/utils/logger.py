import csv
import os
import polars as pl
from datetime import datetime

class DataLogger:
    def __init__(self, filename="sesion_ballenas.csv"):
        # Asegurar directorio
        self.raw_dir = os.path.join("data", "raw")
        os.makedirs(self.raw_dir, exist_ok=True)
        self.filepath = os.path.join(self.raw_dir, filename)
        
        # DEFINICIÓN DE COLUMNAS (SCHEMA)
        # Es vital que coincida con lo que esperamos leer luego
        self.fieldnames = [
            "Timestamp", "timestamp_ms", 
            "Close_Price", "EMA_Princ", "RSI_Val", "ATR_Act", 
            # Datos Micro
            "Micro_Score", "Micro_Buy_Vol", "Micro_Sell_Vol",
            # Datos IA (CRUCIAL: Ahora los definimos explícitamente)
            "Regimen_Actual", 
            "prob_regimen_0", "prob_regimen_1", "prob_regimen_2", 
            "prob_regimen_3", "prob_regimen_4", "prob_regimen_5", "prob_regimen_6"
        ]
        
        # Si el archivo no existe, crearlo con cabeceras
        if not os.path.exists(self.filepath):
            with open(self.filepath, mode='w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                writer.writeheader()

    def guardar_snapshot(self, ts_ms, micro_data, macro_data, df_ticks):
        """
        Guarda una fila en el CSV combinando datos Micro y Macro.
        """
        try:
            # 1. Preparar Timestamp legible
            ts_str = datetime.fromtimestamp(ts_ms / 1000.0).strftime('%Y-%m-%d %H:%M:%S')
            
            # 2. Construir la fila base
            row = {
                "Timestamp": ts_str,
                "timestamp_ms": ts_ms,
                "Close_Price": macro_data.get("Close_Price", 0.0),
                "EMA_Princ": macro_data.get("EMA_Princ", 0.0),
                "RSI_Val": macro_data.get("RSI_Val", 0.0),
                "ATR_Act": macro_data.get("ATR_Act", 0.0),
                
                "Micro_Score": micro_data.get("desbalance", 0.0),
                "Micro_Buy_Vol": micro_data.get("compras", 0),
                "Micro_Sell_Vol": micro_data.get("ventas", 0),
            }

            # 3. EXTRAER DATOS IA (AQUÍ ESTABA EL ERROR)
            # El logger anterior no buscaba estas claves explícitamente.
            
            # Régimen Ganador
            row["Regimen_Actual"] = macro_data.get("Regimen_Actual", 0)
            
            # Probabilidades (Iteramos para extraerlas si existen)
            for i in range(7):
                key = f"prob_regimen_{i}"
                row[key] = macro_data.get(key, 0.0)

            # 4. Escribir al CSV
            with open(self.filepath, mode='a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames, extrasaction='ignore')
                writer.writerow(row)
                
        except Exception as e:
            print(f"[LOGGER ERROR] No se pudo guardar fila: {e}")