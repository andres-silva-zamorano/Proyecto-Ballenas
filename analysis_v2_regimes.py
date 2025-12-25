import polars as pl

def analyze_future_returns_polars():
    print("\n--- ⚡ Análisis Predictivo (Versión Polars) ---")
    
    # 1. Cargar el Dataset (Scan es lazy, muy rápido)
    try:
        # Usamos read_csv si el archivo cabe en RAM, o scan_csv si es gigante
        df = pl.read_csv('Dataset_Con_Regimenes.csv')
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    # Definimos columnas de probabilidad
    prob_cols = [f'prob_regimen_{i}' for i in range(7)]
    
    # Verificación rápida
    if not all(col in df.columns for col in prob_cols):
        print("❌ Faltan columnas 'prob_regimen_X'.")
        return

    print(f"✅ Dataset cargado: {df.height} filas. Procesando...")

    # 2. PROCESAMIENTO (Pipeline Polars) 🚄
    # Horizonte de predicción (velas a futuro)
    LOOK_AHEAD = 5 

    # Diccionario de nombres para el final
    regime_names = {
        0: "0. Lateral (Baja Vol)",
        1: "1. Canal Alcista (Baja Vol)",
        2: "2. Canal Bajista (Baja Vol)",
        3: "3. Canal Alcista (Alta Vol)",
        4: "4. Canal Bajista (Alta Vol)",
        5: "5. Tendencia Alcista CLARA",
        6: "6. Tendencia Bajista CLARA"
    }
    
    # Creamos un DataFrame auxiliar para los nombres
    df_names = pl.DataFrame({
        "Regimen_Dominante": list(regime_names.keys()),
        "Descripcion": list(regime_names.values())
    })

    # --- LA MAGIA DE POLARS ---
    q = (
        df.lazy()
        .with_columns([
            # A: Encontrar el Régimen (argmax horizontal)
            # Creamos una lista por fila y buscamos el índice del valor máximo
            pl.concat_list(prob_cols).list.arg_max().alias("Regimen_Dominante"),
            
            # B: Mirar al futuro (Shift negativo mira hacia adelante)
            pl.col("Close_Price").shift(-LOOK_AHEAD).alias("Future_Close")
        ])
        # Filtramos las últimas 5 filas que quedaron nulas por el shift
        .filter(pl.col("Future_Close").is_not_null())
        .with_columns([
            # C: Calcular Cambio
            (pl.col("Future_Close") - pl.col("Close_Price")).alias("Cambio_Precio")
        ])
        .with_columns([
            # D: Definir si subió (Boolean)
            (pl.col("Cambio_Precio") > 0).alias("Es_Positivo")
        ])
    )

    # 3. AGREGACIÓN (GROUP BY) 📊
    stats = (
        q.group_by("Regimen_Dominante")
        .agg([
            pl.len().alias("Velas (Cant)"),
            pl.col("Cambio_Precio").mean().alias("Cambio Promedio ($)"),
            # En Polars, mean() de un booleano da el porcentaje (0.0 a 1.0)
            (pl.col("Es_Positivo").mean() * 100).alias("Prob. Subida (%)")
        ])
        .collect() # Aquí recién se ejecuta todo el cálculo
    )

    # 4. UNIR CON NOMBRES Y MOSTRAR
    final_df = (
        stats.join(df_names, on="Regimen_Dominante", how="left")
        .sort("Cambio Promedio ($)", descending=True)
        .select(["Descripcion", "Velas (Cant)", "Cambio Promedio ($)", "Prob. Subida (%)"])
    )

    print("-" * 90)
    print(f"📊 RENDIMIENTO A {LOOK_AHEAD} VELAS VISTA (Ordenado por Ganancia):")
    print("-" * 90)
    print(final_df)
    print("-" * 90)

    # 5. CONCLUSIÓN RÁPIDA
    mejor = final_df.row(0)
    peor = final_df.row(-1)
    
    print(f"\n💡 CONCLUSIÓN:")
    print(f"🚀 MEJOR ESCENARIO COMPRAS: {mejor[0]} (Sube {mejor[3]:.1f}% de las veces)")
    print(f"🐻 MEJOR ESCENARIO VENTAS:  {peor[0]} (El precio cae más fuerte)")

if __name__ == "__main__":
    analyze_future_returns_polars()