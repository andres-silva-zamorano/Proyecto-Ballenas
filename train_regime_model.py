import polars as pl
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
import joblib

def train_regime_classifier():
    print("\n--- 🧠 Entrenando Clasificador de Regímenes (V2) ---")

    # 1. Cargar Datos
    try:
        df = pl.read_csv('Dataset_Con_Regimenes.csv')
        print(f"✅ Datos cargados: {df.height} filas.")
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    # 2. Ingeniería de Etiquetas (Target)
    # Reconstruimos cuál era el régimen real basado en las probabilidades del CSV
    prob_cols = [f'prob_regimen_{i}' for i in range(7)]
    
    # Creamos la columna 'Target_Regime' con el número 0-6
    df = df.with_columns(
        pl.concat_list(prob_cols).list.arg_max().alias("Target_Regime")
    )

    # 3. Selección de Features (Lo que la IA verá en tiempo real)
    # Quitamos las columnas 'prob_', 'Future', 'Profit', etc.
    # Nos quedamos solo con indicadores técnicos que SI tenemos en vivo.
    feature_cols = [
        'ATR_Act', 'ATR_Rel', 'EMA_Princ', 'ADX_Val', 
        'RSI_Val', 'MACD_Val', 'DI_Plus', 'DI_Minus',
        'EMA_10', 'EMA_20', 'EMA_40', 'EMA_80', 'EMA_Slope_Princ', # Ajusta nombres si difieren
        'ADX_Diff', 'RSI_Velocidad', 'Volumen_Relativo'
    ]
    
    # Filtramos columnas que realmente existan en el CSV
    valid_features = [c for c in feature_cols if c in df.columns]
    print(f"✅ Usando {len(valid_features)} indicadores para detectar el régimen.")

    # 4. Preparar X (Features) e y (Target)
    # Convertimos a Pandas/Numpy para Scikit-Learn (Polars aún no tiene ML nativo completo)
    data_pd = df.select(valid_features + ["Target_Regime"]).to_pandas().dropna()
    
    X = data_pd[valid_features]
    y = data_pd["Target_Regime"]

    # 5. Split Train/Test
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # 6. Entrenar Random Forest
    print("⏳ Entrenando modelo (esto puede tardar unos segundos)...")
    clf = RandomForestClassifier(
        n_estimators=100, 
        max_depth=15, 
        n_jobs=-1, 
        random_state=42
    )
    clf.fit(X_train, y_train)

    # 7. Evaluar
    y_pred = clf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"\n🎯 Precisión Global del Modelo: {acc*100:.2f}%")
    print("\nDetalle por Régimen:")
    print(classification_report(y_test, y_pred))

    # 8. Guardar el Modelo
    joblib.dump(clf, 'regime_classifier.pkl')
    joblib.dump(valid_features, 'regime_features_list.pkl') # Guardamos nombres de columnas para no confundirnos luego
    print("💾 Modelo guardado como: 'regime_classifier.pkl'")
    print("💾 Lista de features guardada como: 'regime_features_list.pkl'")

if __name__ == "__main__":
    train_regime_classifier()