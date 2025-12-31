import optuna
import os
import sys
# Añadir ruta raíz para importar módulos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.models.backtest_engine import BacktestEngine

def objective(trial):
    # 1. Definir el espacio de búsqueda (Los parámetros que queremos optimizar)
    umbral = trial.suggest_float("umbral_ballena", 0.05, 0.30)
    sl = trial.suggest_float("stop_loss", 0.001, 0.02) # 0.1% a 2%
    tp = trial.suggest_float("take_profit", 0.002, 0.05) # 0.2% a 5%
    tf = trial.suggest_categorical("timeframe", [1, 5, 15]) # Minutos
    
    # 2. Instanciar Motor
    path = os.path.join("data", "raw", "sesion_ballenas.csv")
    engine = BacktestEngine(path)
    
    if not engine.cargar_datos():
        return 0.0
    
    # 3. Ejecutar Simulación
    resultado = engine.ejecutar_simulacion(
        umbral_ballena=umbral,
        stop_loss_pct=sl,
        take_profit_pct=tp,
        timeframe_min=tf
    )
    
    # 4. Definir qué queremos maximizar (Profit o ROI)
    # Penalizamos si hace muy pocos trades (menos de 5 no es estadístico)
    if resultado["trades_total"] < 5:
        return -9999
        
    return resultado["balance_final"]

def ejecutar_optimizacion():
    print("--- 🧠 INICIANDO BÚSQUEDA DE HIPERPARÁMETROS (OPTUNA) ---")
    
    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=100) # Probará 100 combinaciones
    
    print("\n🏆 MEJOR ESTRATEGIA ENCONTRADA:")
    print(f"   Balance Final: ${study.best_value:.2f}")
    print("   Parámetros:")
    for key, value in study.best_params.items():
        print(f"     - {key}: {value}")

if __name__ == "__main__":
    ejecutar_optimizacion()