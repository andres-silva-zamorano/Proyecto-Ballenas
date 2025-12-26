import csv
import os
from datetime import datetime, timedelta, timezone

class DataLogger:
    def __init__(self, filename="Dataset_Con_Regimenes_LIVE.csv"):
        # Ruta de guardado
        self.filepath = os.path.join("data", "raw", filename)
        
        # --- CALIBRACIÓN HORARIA ---
        # Ajusta aquí según la diferencia que viste en tu escáner.
        self.BROKER_OFFSET_HOURS = 0      
        self.BROKER_OFFSET_MINUTES = 0    
        
        # --- DEFINICIÓN DE COLUMNAS ---
        self.columns = [
            "Timestamp", "Resultado_Final", "Num_Intentos", "Accion_Inicial",
            "ATR_Act", "ATR_Rel", "EMA_Princ", "ADX_Val", 
            "Regimen_Actual",
            "RSI_Val", "MACD_Val", "DI_Plus", "DI_Minus",
            "EMA_10", "EMA_20", "EMA_40", "EMA_80", "EMA_160", "EMA_320",
            "SL_Factor_ATR", "EMA_Princ_Slope", "ADX_Diff", "RSI_Velocidad",
            "Volumen_Relativo", "Close_Price", "Deal_Ticket", "Real_Profit",
            # Probabilidades
            "prob_regimen_0", "prob_regimen_1", "prob_regimen_2", 
            "prob_regimen_3", "prob_regimen_4", "prob_regimen_5", "prob_regimen_6",
            # Microestructura
            "Micro_Score", "Micro_Buy_Vol", "Micro_Sell_Vol"
        ]
        
        self.headers_written = False
        self._inicializar_archivo()

    def _inicializar_archivo(self):
        """
        Verifica si el archivo existe Y si tiene contenido.
        Si existe pero está vacío (0 bytes), marcamos headers_written = False 
        para escribirlos de nuevo.
        """
        if os.path.exists(self.filepath) and os.path.getsize(self.filepath) > 0:
            self.headers_written = True
        else:
            self.headers_written = False

    def guardar_snapshot(self, ts_ms, micro, macro, ticks_df):
        if not macro: 
            return

        # 1. Cálculo de Hora Servidor
        dt_utc = datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc)
        dt_broker = dt_utc + timedelta(
            hours=self.BROKER_OFFSET_HOURS, 
            minutes=self.BROKER_OFFSET_MINUTES
        )
        timestamp_str = dt_broker.strftime("%Y-%m-%d %H:%M:%S")

        # 2. Construcción de Fila
        row = {
            "Timestamp": timestamp_str,
            "Resultado_Final": 0, "Num_Intentos": 0, "Accion_Inicial": 0,
            
            "ATR_Act": macro.get("ATR_Act", 0),
            "ATR_Rel": macro.get("ATR_Rel", 0),
            "EMA_Princ": macro.get("EMA_Princ", 0),
            "ADX_Val": macro.get("ADX_Val", 0),
            "Regimen_Actual": 0, 
            "RSI_Val": macro.get("RSI_Val", 0),
            "MACD_Val": macro.get("MACD_Val", 0),
            "DI_Plus": 0, "DI_Minus": 0,
            "EMA_10": macro.get("EMA_10", 0), "EMA_20": macro.get("EMA_20", 0),
            "EMA_40": macro.get("EMA_40", 0), "EMA_80": macro.get("EMA_80", 0),
            "EMA_160": macro.get("EMA_160", 0), "EMA_320": macro.get("EMA_320", 0),
            
            "SL_Factor_ATR": 3.0,
            "EMA_Princ_Slope": macro.get("EMA_Princ_Slope", 0),
            "ADX_Diff": 0, "RSI_Velocidad": 0,
            "Volumen_Relativo": 1.0,
            "Close_Price": macro.get("Close_Price", 0),
            "Deal_Ticket": 0, "Real_Profit": 0,
            
            "prob_regimen_0": 0.0, "prob_regimen_1": 0.0, "prob_regimen_2": 0.0,
            "prob_regimen_3": 0.0, "prob_regimen_4": 0.0, "prob_regimen_5": 0.0, 
            "prob_regimen_6": 0.0,
            
            "Micro_Score": micro.get("desbalance", 0),
            "Micro_Buy_Vol": micro.get("compras", 0),
            "Micro_Sell_Vol": micro.get("ventas", 0)
        }

        # 3. Escritura Segura
        try:
            with open(self.filepath, mode='a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.columns)
                
                # CRÍTICO: Si no se han escrito headers, escribirlos ahora
                if not self.headers_written:
                    writer.writeheader()
                    self.headers_written = True
                
                writer.writerow(row)
                
        except Exception as e:
            print(f"[LOGGER ERROR] No se pudo escribir en CSV: {e}")