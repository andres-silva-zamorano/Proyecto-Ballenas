import polars as pl
import numpy as np
import os
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from sklearn.preprocessing import StandardScaler

class SupervisedTrainerV2:
    def __init__(self, data_path, model_dir):
        self.data_path = data_path
        self.model_dir = model_dir
        
        # INPUTS: Lo que la IA mira para tomar la decisión
        self.features = [
            "ATR_Rel",          
            "RSI_Val",          
            "MACD_Val",         
            "ADX_Val",          
            "EMA_Princ_Slope",  
            "Volumen_Relativo"  
        ]
        
        # COLUMNAS DE LA VERDAD (Probabilidades históricas)
        self.prob_cols = [f"prob_regimen_{i}" for i in range(7)]

    def entrenar(self):
        print("--- ENTRENAMIENTO SUPERVISADO V2 (CORREGIDO) ---")
        
        # 1. Cargar Datos
        if not os.path.exists(self.data_path):
            print(f"ERROR: No existe {self.data_path}")
            return
            
        print(f"[1] Cargando dataset: {self.data_path}")
        df = pl.read_parquet(self.data_path)
        
        # 2. GENERACIÓN DE ETIQUETAS (EL PASO QUE FALTABA)
        # Buscamos cuál de las 7 columnas tiene el valor más alto y ese será el ID del régimen
        print("[2] Calculando el 'Régimen Ganador' para cada vela...")
        
        # Usamos Polars para encontrar el índice del valor máximo horizontalmente
        # Esto crea una columna con números 0-6
        df_labeled = df.with_columns(
            pl.concat_list(self.prob_cols).list.arg_max().alias("Target_Regimen")
        )
        
        # AUDITORÍA DE CLASES: Verificar que ahora sí tenemos variedad
        conteo = df_labeled["Target_Regimen"].value_counts().sort("Target_Regimen")
        print("\n    Distribución REAL de clases encontrada:")
        print(conteo)
        
        # Verificar si seguimos teniendo solo ceros
        if df_labeled["Target_Regimen"].n_unique() < 2:
            print("🔴 ERROR: Seguimos teniendo una sola clase. Revisa las columnas de probabilidad.")
            return

        # 3. Preparar X (Features) e y (Target Calculado)
        print(f"\n[3] Preparando matrices de entrenamiento...")
        
        # Filtrar filas donde falten features
        df_clean = df_labeled.drop_nulls(subset=self.features + ["Target_Regimen"])
        
        X = df_clean.select(self.features).to_numpy()
        y = df_clean.select("Target_Regimen").to_numpy().ravel()
        
        # Limpieza de seguridad (NaNs en inputs a 0)
        X = np.nan_to_num(X, nan=0.0)
        
        # 4. Escalar Datos
        print("[4] Normalizando datos (StandardScaler)...")
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # 5. Dividir Train/Test
        X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42, shuffle=False)

        # 6. Entrenar Modelo
        print(f"[5] Entrenando Random Forest con {len(X_train)} ejemplos...")
        # Aumentamos un poco la profundidad ya que tenemos muchos datos reales
        rf_model = RandomForestClassifier(n_estimators=100, max_depth=20, random_state=42, n_jobs=-1)
        rf_model.fit(X_train, y_train)

        # 7. Evaluar
        print("[6] Evaluando precisión real...")
        y_pred = rf_model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        
        print(f"    -> PRECISIÓN GLOBAL: {acc:.2%}")
        print("    -> Reporte por Régimen:")
        print(classification_report(y_test, y_pred))

        # 8. Guardar
        print("[7] Guardando modelos...")
        os.makedirs(self.model_dir, exist_ok=True)
        
        path_scaler = os.path.join(self.model_dir, "scaler.pkl")
        path_model = os.path.join(self.model_dir, "rf_model.pkl")
        
        joblib.dump(scaler, path_scaler)
        joblib.dump(rf_model, path_model)
        
        print(f"    -> LISTO. Modelos guardados en {self.model_dir}")

if __name__ == "__main__":
    DATA_PATH = os.path.join("data", "processed", "dataset_entrenamiento.parquet")
    MODEL_DIR = os.path.join("models")
    
    trainer = SupervisedTrainerV2(DATA_PATH, MODEL_DIR)
    trainer.entrenar()