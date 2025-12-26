import joblib
import numpy as np
import os
import pandas as pd # Usamos pandas para manejo rápido de dict a df en inferencia

class MarketPredictor:
    def __init__(self, model_dir="models"):
        self.scaler_path = os.path.join(model_dir, "scaler.pkl")
        self.model_path = os.path.join(model_dir, "rf_model.pkl")
        self.model = None
        self.scaler = None
        self.loaded = False
        
        # EL ORDEN DEBE SER EXACTAMENTE EL MISMO DEL ENTRENAMIENTO
        self.features = [
            "ATR_Rel",          
            "RSI_Val",          
            "MACD_Val",         
            "ADX_Val",          
            "EMA_Princ_Slope",  
            "Volumen_Relativo"  
        ]
        
        self._cargar_modelos()

    def _cargar_modelos(self):
        try:
            if os.path.exists(self.scaler_path) and os.path.exists(self.model_path):
                self.scaler = joblib.load(self.scaler_path)
                self.model = joblib.load(self.model_path)
                self.loaded = True
                print(f"[IA] Modelos cargados exitosamente desde {self.scaler_path}")
            else:
                print("[IA ERROR] No se encontraron los archivos .pkl en 'models/'")
        except Exception as e:
            print(f"[IA CRITICAL] Error cargando cerebros: {e}")

    def predecir(self, macro_data: dict):
        """
        Recibe el diccionario de indicadores actuales y devuelve:
        - regimen_id (int): 0 a 6
        - probabilidades (list): [p0, p1, ... p6]
        """
        if not self.loaded or not macro_data:
            # Retorno seguro si falla algo
            return 0, [0.0]*7

        try:
            # 1. Extraer features en el orden correcto
            # Si falta alguno, asumimos 0.0 para no romper el sistema
            row = [macro_data.get(f, 0.0) for f in self.features]
            
            # 2. Convertir a numpy y reformatear (1 fila, N columnas)
            X = np.array(row).reshape(1, -1)
            
            # 3. Escalar (Normalizar)
            X_scaled = self.scaler.transform(X)
            
            # 4. Predecir
            regimen = self.model.predict(X_scaled)[0]
            probs = self.model.predict_proba(X_scaled)[0]
            
            return int(regimen), probs.tolist()
            
        except Exception as e:
            # Si pasa algo raro (ej. dato infinito), retornamos neutral
            return 0, [0.0]*7