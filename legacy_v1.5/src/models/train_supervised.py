import polars as pl
import numpy as np
import os
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from sklearn.preprocessing import StandardScaler

class SupervisedTrainer:
    def __init__(self, data_path, model_dir):
        self.data_path = data_path
        self.model_dir = model_dir
        
        # --- INPUTS (Lo que la IA ve) ---
        # Estas son las variables que usará para decidir qué régimen es.
        self.features = [
            "ATR_Rel",          
            "RSI_Val",          
            "MACD_Val",         
            "ADX_Val",          
            "EMA_Princ_Slope",  
            "Volumen_Relativo"  
        ]
        
        # --- TARGET (Lo que la IA debe aprender a predecir) ---
        self.target = "Regimen_Actual" # Debe ser un número entero (0 a 6)

    def entrenar(self):
        print("--- INICIANDO ENTRENAMIENTO SUPERVISADO (RANDOM FOREST) ---")
        
        # 1. Cargar Datos
        if not os.path.exists(self.data_path):
            print(f"ERROR: No existe {self.data_path}")
            return
            
        print(f"[1] Cargando dataset: {self.data_path}")
        df = pl.read_parquet(self.data_path)
        
        # Verificar que existen las columnas necesarias
        cols_necesarias = self.features + [self.target]
        missing = [c for c in cols_necesarias if c not in df.columns]
        if missing:
            print(f"ERROR CRÍTICO: Faltan columnas en el dataset: {missing}")
            print("Asegúrate de que tu histórico tenga 'Regimen_Actual' lleno.")
            return

        # 2. Preparar X (Features) e y (Target)
        print(f"[2] Preparando datos...")
        X_df = df.select(self.features)
        y_df = df.select(self.target)
        
        X = X_df.to_numpy()
        y = y_df.to_numpy().ravel() # Aplanar array
        
        # Limpieza de seguridad (NaNs)
        X = np.nan_to_num(X, nan=0.0)
        
        # 3. Escalar Datos (Scaler)
        # Aunque Random Forest no exige escalar, es buena práctica para uniformidad
        print("[3] Normalizando datos (StandardScaler)...")
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # 4. Dividir en Entrenamiento (80%) y Prueba (20%)
        # Esto es vital para saber si la IA aprendió de verdad o solo memorizó
        X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42, shuffle=False)
        # shuffle=False es importante en Time Series, pero si los regímenes son independientes vela a vela, True está bien.
        # Usaremos False para respetar un poco la temporalidad, aunque Random Forest es agnóstico al tiempo.

        # 5. Entrenar Modelo
        print(f"[4] Entrenando Random Forest con {len(X_train)} ejemplos...")
        # n_estimators=100 árboles, max_depth=10 para no sobreajustar
        rf_model = RandomForestClassifier(n_estimators=100, max_depth=15, random_state=42, n_jobs=-1)
        rf_model.fit(X_train, y_train)

        # 6. Evaluar
        print("[5] Evaluando precisión...")
        y_pred = rf_model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        print(f"    -> PRECISIÓN GLOBAL: {acc:.2%}")
        print("    -> Reporte detallado:")
        print(classification_report(y_test, y_pred))

        # 7. Guardar el Cerebro
        print("[6] Guardando modelos...")
        os.makedirs(self.model_dir, exist_ok=True)
        
        path_scaler = os.path.join(self.model_dir, "scaler.pkl")
        path_model = os.path.join(self.model_dir, "rf_model.pkl") # Cambiamos nombre a rf_model
        
        joblib.dump(scaler, path_scaler)
        joblib.dump(rf_model, path_model)
        
        print(f"    -> Scaler guardado en: {path_scaler}")
        print(f"    -> Modelo guardado en: {path_model}")
        print("--- ENTRENAMIENTO EXITOSO ---")

if __name__ == "__main__":
    DATA_PATH = os.path.join("data", "processed", "dataset_entrenamiento.parquet")
    MODEL_DIR = os.path.join("models")
    
    trainer = SupervisedTrainer(DATA_PATH, MODEL_DIR)
    trainer.entrenar()