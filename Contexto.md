# PROYECTO MAESTRO: [Proyecto Ballenas]

**Versión Actual:** `v1.0-alpha`
**Activo Objetivo:** BTCUSD (Bitcoin)
**Plataforma Base:** MetaTrader 5 (MT5) + Python

---

## 1. Descripción General
El **Proyecto Ballenas** consiste en el desarrollo de un sistema de trading avanzado ("Caja Negra") diseñado para detectar la actividad de las "Manos Fuertes" o "Ballenas" institucionales en el mercado de criptomonedas (inicialmente BTCUSD).

El sistema ingiere datos técnicos y probabilidades de regímenes de mercado para determinar si el precio está siendo manipulado, acumulado (compras institucionales) o distribuido (ventas institucionales). El objetivo final es alinearse con estos movimientos de gran volumen.

### El Concepto de "Caja Negra"
* **Entrada:** Indicadores Técnicos (ADX, ATR, EMA, RSI, etc.) + Probabilidades de 7 Regímenes de Mercado.
* **Procesamiento:** Modelos de Machine Learning (Clasificación, Redes Neuronales) optimizados con Optuna.
* **Salida:** Detección de intención institucional (Compra/Venta/Espera) y predicción de movimiento futuro.

---

## 2. Arquitectura de Datos

El sistema se alimenta de un dataset de 15 meses de historia (velas de 1 minuto), enriquecido con probabilidades de regímenes.

### Diccionario de Datos: `Dataset_Masivo_Optuna`
### Nombre Archivo: "Dataset_Con_Regimenes.csv"

| Columna | Tipo | Origen | Descripción |
| :--- | :--- | :--- | :--- |
| **Timestamp** | String | `TimeToString` | Fecha/Hora cierre vela (Minuto). `YYYY.MM.DD HH:MM`. |
| **Resultado_Final** | Int | Fijo (`0`) | *Placeholder*. Target del modelo (ej. Win/Loss). |
| **Num_Intentos** | Int | Fijo (`0`) | *Placeholder*. Conteo de intentos. |
| **Accion_Inicial** | Int | Fijo (`1`) | *Placeholder*. Acción simulada (1=Buy, -1=Sell). |
| **ATR_Act** | Float | Sensor | Volatilidad actual (Average True Range). |
| **ATR_Rel** | Float | Sensor | ATR Relativo (normalizado). |
| **EMA_Princ** | Float | Sensor | EMA Principal (Tendencia base). |
| **ADX_Val** | Float | Sensor | Fuerza de la tendencia (ADX). |
| **Regimen_Actual** | Int | Fijo (`0`) | *Placeholder*. ID del régimen dominante. |
| **RSI_Val** | Float | Sensor | Momentum (RSI). |
| **MACD_Val** | Float | Sensor | Indicador MACD. |
| **DI_Plus** | Float | Sensor | Direccional Positivo (+DI). |
| **DI_Minus** | Float | Sensor | Direccional Negativo (-DI). |
| **EMA_10 ... EMA_320**| Float | Sensor | EMAs de periodos 10, 20, 40, 80, 160, 320. |
| **SL_Factor_ATR** | Float | Fijo (`3.0`) | Multiplicador para Stop Loss dinámico. |
| **EMA_Princ_Slope** | Float | Sensor | Ángulo/Pendiente de la EMA Principal. |
| **ADX_Diff** | Float | Sensor | Aceleración de la tendencia (Diferencial ADX). |
| **RSI_Velocidad** | Float | Sensor | Velocidad del cambio en RSI. |
| **Volumen_Relativo** | Float | Sensor | Ratio Volumen Actual vs Promedio. |
| **Close_Price** | Float | `iClose` | Precio de cierre (M1). |
| **Deal_Ticket** | Int | Fijo (`0`) | *Placeholder*. ID transacción Broker. |
| **Real_Profit** | Float | Fijo (`0`) | *Placeholder*. Beneficio futuro (Target Regresión). |
| **prob_regimen_0** | Float | Sensor | Prob. **Canal Lateral** (Rango estático). |
| **prob_regimen_1** | Float | Sensor | Prob. **Canal Alcista (Baja Volatilidad)**. |
| **prob_regimen_2** | Float | Sensor | Prob. **Canal Bajista (Baja Volatilidad)**. |
| **prob_regimen_3** | Float | Sensor | Prob. **Canal Alcista (Alta Volatilidad)**. |
| **prob_regimen_4** | Float | Sensor | Prob. **Canal Bajista (Alta Volatilidad)**. |
| **prob_regimen_5** | Float | Sensor | Prob. **Tendencia Alcista Clara**. |
| **prob_regimen_6** | Float | Sensor | Prob. **Tendencia Bajista Clara**. |

---

## 3. Stack Tecnológico

El desarrollo es 100% en **Python**, priorizando modularidad y escalabilidad.

1.  **Conectividad:** `MetaTrader5` (Librería Python oficial) para obtención de datos en tiempo real y ejecución de órdenes.
2.  **Procesamiento de Datos:** `Polars`, `numpy`.
3.  **Machine Learning (Clasificación):** `scikit-learn` (Árboles de decisión, Random Forest, etc.) para detección de regímenes y señales.
4.  **Deep Learning:** `TensorFlow` / `Keras` o `PyTorch` (Redes Neuronales profundas).
5.  **Optimización:** `Optuna`. Indispensable para el ajuste de hiperparámetros tanto de modelos ML como de lógica de trading.

---

## 4. Roadmap y Fases del Proyecto

### Fase 1: Asistencia Manual (Híbrido)
*Estado Actual: En desarrollo (v1.0-alpha)*
*Meta al finalizar: v1.0-Beta*

#### Etapa 1.A: Monitor en Tiempo Real
Desarrollo de una consola/terminal en Python que monitorea el mercado en vivo.
* **Funcionalidad:**
    * Se conecta a MT5 y extrae datos cada minuto.
    * Procesa la información con la Red Neuronal y los clasificadores ya entrenados/optimizados.
    * **Output:** Muestra en pantalla el régimen actual, si hay manipulación de precios, absorción de energía y la intención de las "Manos Fuertes" (Comprando/Vendiendo).
* **Operativa:** El trader observa la consola y ejecuta las órdenes manualmente en MT5 basándose en la recomendación del sistema.

#### Etapa 1.B: Validación Histórica (Backtest Corto)
Validación de la lógica de "Manos Fuertes" en el pasado reciente.
* **Funcionalidad:**
    * Analizar una ventana de tiempo hacia atrás (10 a 15 días).
    * Generar un reporte: "Desde Día X Hora Y hasta Día A Hora B, las ballenas compraron".
    * Comparar visualmente en el gráfico si el precio efectivamente subió/bajó después de esos periodos de acumulación/distribución detectados.

### Fase 2: Automatización Total
*Versión objetivo: v2.0-alpha*

* **Implementación:** Desarrollo del Robot (Bot) 100% autónomo.
* **Capacidades:**
    * Entra y sale del mercado sin intervención humana.
    * Genera informes de eficiencia y actividad diaria.
    * **Auto-mejoramiento:** Capacidad de re-entrenar la red neuronal periódicamente para adaptarse a la evolución del mercado.

---

## 5. Reglas Críticas de Desarrollo (Mandamientos)

1.  **Modularidad Extrema:** El código Python debe estar organizado en un árbol de archivos lógico. Nada de scripts monolíticos gigantes.
2.  **Orquestación:** Debe existir un archivo principal (Orquestador) que llame y coordine los módulos (Data, ML, Connection, Strategy).
3.  **Escalabilidad:** La estructura debe permitir agregar nuevos indicadores o cambiar modelos de ML sin romper todo el sistema.
4.  **Optimización Continua:** Uso obligatorio de `Optuna` para encontrar los mejores parámetros en cada etapa de experimentación.
5.  **Documentación en Código:** Funciones y clases deben tener *Docstrings* claros explicando qué hacen, entradas y salidas.
6.  **Conexión Híbrida:** Aunque el entrenamiento es con CSV (histórico), la producción debe usar obligatoriamente la librería `MetaTrader5` de Python.
7.  **No se usará librería Pandas:** Usaremos siempre la libreria Polars, jamás usaremos la librería Pandas.

---

## 6. Estructura de Archivos Sugerida (Draft)

```text
proyecto_ballenas/
│
├── data/
│   ├── raw/                   # CSVs originales (Dataset_Con_Regimenes.csv)
│   ├── processed/             # CSVs limpios o con ingeniería de características
│   └── models/                # Archivos .pkl o .h5 (modelos entrenados)
│
├── src/
│   ├── connection/
│   │   └── mt5_connector.py   # Wrapper para funciones de MetaTrader5
│   │
│   ├── features/
│   │   ├── indicators.py      # Cálculo de ADX, ATR, EMA, etc.
│   │   └── regimes.py         # Lógica de detección de los 7 regímenes
│   │
│   ├── models/
│   │   ├── trainer.py         # Lógica de entrenamiento (sklearn/NN)
│   │   ├── optimizer.py       # Scripts de Optuna
│   │   └── predictor.py       # Carga modelos y genera predicciones
│   │
│   ├── strategies/
│   │   └── whale_detector.py  # Lógica de negocio (Manos Fuertes, Absorción)
│   │
│   └── utils/
│       └── logger.py          # Sistema de logs y reportes
│
├── main_monitor_v1.py         # Orquestador para Etapa 1 (Consola)
├── backtest_validator_v1.py   # Script para Etapa 1.B (10-15 días)
├── main_auto_v2.py            # Orquestador futuro para Etapa 2
├── requirements.txt           # Dependencias (Polars, sklearn, optuna, etc.)
└── CONTEXTO_PROYECTO.md       # Este archivo