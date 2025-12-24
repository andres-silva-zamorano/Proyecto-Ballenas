# train_model.py
import polars as pl
import numpy as np
import optuna
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_score
import joblib
import data_loader
import indicators
import feature_engineering
import config

def train_and_save():
    print(f"--- 🚀 Entrenando IA para {config.SYMBOL} ({config.TIMEFRAME}m) ---")
    
    # 1. Conexión y Descarga
    if not data_loader.initialize_mt5(): return

    print("1. Descargando historial de velas (15.000 mins)...")
    # Descargamos ~10 días de datos minuto a minuto
    df_candles = data_loader.get_candles(config.SYMBOL, config.TIMEFRAME, n_candles=15000)
    
    if df_candles is None: return

    print("2. Descargando historial de ticks (Esto puede tardar)...")
    start_date = df_candles["time"][0]
    df_ticks = data_loader.get_ticks(config.SYMBOL, start_date)
    
    if df_ticks is None: return
    
    # 2. Ingeniería de Features (Polars)
    print("3. Calculando CVD Sintético y Features...")
    cvd = indicators.calculate_synthetic_cvd(df_ticks, config.TIMEFRAME_POLARS)
    df = feature_engineering.create_dataset(df_candles, cvd)
    df = feature_engineering.add_targets(df)
    
    # 3. Preparación para Scikit-Learn (Polars -> Pandas)
    # Scikit-Learn trabaja mejor con Numpy/Pandas
    df_pandas = df.to_pandas()
    
    features = ['z_score', 'trfi', 'cvd_slope', 'momentum_3', 'volatility']
    X = df_pandas[features]
    y = df_pandas['target']
    
    # OPCIONAL: Filtrar el ruido (Clase 0) para forzar a la IA a buscar solo entradas claras
    # mask = y != 0
    # X, y = X[mask], y[mask]
    
    # Split secuencial (respetando el tiempo)
    split = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]
    
    print(f"   Datos entrenamiento: {len(X_train)} | Datos validación: {len(X_test)}")

    # 4. Optimización con Optuna
    print("4. Optimizando Hiperparámetros (Buscando la mejor configuración)...")
    
    def objective(trial):
        param = {
            'n_estimators': trial.suggest_int('n_estimators', 50, 300),
            'max_depth': trial.suggest_int('max_depth', 3, 15),
            'min_samples_split': trial.suggest_int('min_samples_split', 2, 20),
            'n_jobs': -1,
            'random_state': 42
        }
        
        clf = RandomForestClassifier(**param)
        clf.fit(X_train, y_train)
        preds = clf.predict(X_test)
        
        # Maximizamos la Precisión (Evitar entrar en operaciones perdedoras)
        return precision_score(y_test, preds, average='weighted', zero_division=0)

    study = optuna.create_study(direction='maximize')
    study.optimize(objective, n_trials=50) # 10 pruebas rápidas
    
    print(f"   Mejor Precisión lograda: {study.best_value:.2%}")
    print(f"   Mejores parámetros: {study.best_params}")
    
    # 5. Guardar el Modelo Campeón
    print("5. Guardando cerebro (.pkl)...")
    best_model = RandomForestClassifier(**study.best_params, random_state=42)
    best_model.fit(X, y) # Entrenar con TODO el historial
    
    joblib.dump(best_model, config.MODEL_FILENAME)
    print("✅ Entrenamiento finalizado con éxito.")

if __name__ == "__main__":
    train_and_save()
