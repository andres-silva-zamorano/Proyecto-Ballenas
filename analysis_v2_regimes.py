# analysis_v2_regimes.py
import pandas as pd
import numpy as np

def analyze_regimes():
    print("--- 🔬 Análisis de Regímenes de Mercado (Versión 2.0) ---")
    
    # 1. Cargar el Dataset
    try:
        df = pd.read_csv('Dataset_Con_Regimenes.csv')
        print(f"✅ Dataset cargado: {df.shape[0]} filas.")
    except FileNotFoundError:
        print("❌ Error: No encuentro 'Dataset_Con_Regimenes.csv'. Súbelo al servidor.")
        return

    # 2. Limpieza básica
    # Convertimos Profit a número por si acaso
    df['Real_Profit'] = pd.to_numeric(df['Real_Profit'], errors='coerce').fillna(0)
    
    # Definimos los nombres de los regímenes (según tu descripción)
    regime_names = {
        0: "0. Lateral (Baja Vol)",
        1: "1. Canal Alcista (Baja Vol)",
        2: "2. Canal Bajista (Baja Vol)",
        3: "3. Canal Alcista (Alta Vol)",
        4: "4. Canal Bajista (Alta Vol)",
        5: "5. Tendencia Alcista CLARA",
        6: "6. Tendencia Bajista CLARA"
    }

    # 3. Agrupar por 'Regimen_Actual' y calcular estadísticas
    # Asumimos que la columna se llama 'Regimen_Actual' basándonos en tu CSV
    if 'Regimen_Actual' not in df.columns:
        print("⚠️ No encuentro la columna 'Regimen_Actual'. Revisando columnas...")
        print(df.columns.tolist())
        return

    stats = df.groupby('Regimen_Actual')['Real_Profit'].agg([
        'count',            # Cuántas velas hay de este tipo
        'sum',              # Profit Total acumulado
        'mean',             # Profit Promedio por vela
        lambda x: (x > 0).mean() * 100  # Win Rate (Probabilidad de Ganancia)
    ])

    # Renombrar columnas para que se vea bonito
    stats.columns = ['Velas (Cant)', 'Profit Total', 'Profit Promedio', 'Win Rate (%)']
    
    # Mapear los nombres de los regímenes
    stats.index = stats.index.map(regime_names)

    # 4. Mostrar Resultados
    print("\n📊 RENDIMIENTO POR RÉGIMEN:")
    print("-" * 80)
    # Ordenamos por Profit Total para ver cuál da más dinero
    print(stats.sort_values(by='Profit Total', ascending=False))
    print("-" * 80)

    # 5. La "Joya de la Corona": Filtrado Inteligente
    # Vamos a ver qué pasa si filtramos por ADX fuerte (> 25)
    if 'ADX_Val' in df.columns:
        print("\n🔎 ZOOM: ¿Mejora si filtramos por ADX > 25 (Tendencia Fuerte)?")
        df_adx = df[df['ADX_Val'] > 25]
        stats_adx = df_adx.groupby('Regimen_Actual')['Real_Profit'].mean()
        stats_adx.index = stats_adx.index.map(regime_names)
        print(stats_adx)

if __name__ == "__main__":
    analyze_regimes()