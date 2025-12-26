# PROYECTO MAESTRO: [Proyecto Ballenas]

**Versión Actual:** `v1.0-alpha`
**Activo Objetivo:** BTCUSD (Bitcoin)
**Plataforma Base:** MetaTrader 5 (MT5) + Python

---

## 1. Descripción General
El **Proyecto Ballenas** consiste en el desarrollo de un sistema de trading avanzado ("Caja Negra") diseñado para detectar la actividad de las "Manos Fuertes" o "Ballenas" institucionales en el mercado de criptomonedas (inicialmente BTCUSD).

El sistema ingiere datos técnicos de alta frecuencia (Tics) y probabilidades de regímenes de mercado para determinar si el precio está siendo manipulado, acumulado (compras institucionales) o distribuido (ventas institucionales). El objetivo final es alinearse con estos movimientos de gran volumen.

### El Concepto de "Caja Negra"
* **Entrada:** Flujo de Tics separado (Bid Stream vs Ask Stream), Indicadores Técnicos y Probabilidades de Regímenes.
* **Procesamiento:** Modelos de Machine Learning (Clustering, Redes Neuronales Híbridas) optimizados con Optuna.
* **Salida:** Detección de intención institucional y **Señales de Transición de Estado** (Flip Comprador/Vendedor).

---

## 2. Arquitectura de Datos

El sistema se alimenta de un dataset enriquecido que combina estructura de tics y análisis de regímenes.

### Diccionario de Datos
**Nombre del Archivo:** `Dataset_Con_Regimenes.csv` (Histórico)
*Nota: Para tiempo real, ver restricciones en Sección 5.*

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

El desarrollo es 100% en **Python**, priorizando modularidad, eficiencia y escalabilidad.

1.  **Conectividad:** `MetaTrader5` (Librería Python oficial) para obtención de datos en tiempo real (Tics).
2.  **Procesamiento de Datos:** `Polars` (Estrictamente sobre Pandas por rendimiento) y `numpy`.
3.  **Machine Learning (Clasificación/Clustering):** `scikit-learn`. Uso de **K-Means** y **DBSCAN** para segmentación de participantes.
4.  **Deep Learning:** `TensorFlow` / `Keras` o `PyTorch`. Se utilizarán arquitecturas híbridas **CNN-GRU-Attention**. La GRU (Gated Recurrent Unit) proveerá la "memoria" de la serie temporal, optimizando el coste computacional frente a LSTM.
5.  **Optimización:** `Optuna`. Indispensable para la optimización Bayesiana de hiperparámetros (TPE).

---

## 4. Roadmap y Fases del Proyecto

### Fase 1: Asistencia Manual (Híbrido)
*Estado Actual: En desarrollo (v1.0-alpha)*
*Meta al finalizar: v1.0-Beta*

#### Etapa 1.A: Monitor en Tiempo Real
Desarrollo de una consola/terminal en Python que monitorea el mercado en vivo.
* **Funcionalidad:**
    * Se conecta a MT5 y extrae datos cada minuto/tic.
    * **Output Crítico:** Emite una **SEÑAL (Mensaje/Pitido)** cuando detecta el cambio de estado (Flip):
        * De *Intención Vendedora* (Bid Pressure) -> a *Intención Compradora* (Ask Pressure).
        * De *Intención Compradora* (Ask Pressure) -> a *Intención Vendedora* (Bid Pressure).
* **Operativa:** El trader observa la consola y ejecuta las órdenes manualmente en MT5 basándose en la recomendación del sistema.

#### Etapa 1.B: Validación Histórica (Backtest Corto)
Validación de la lógica de "Manos Fuertes" en el pasado reciente.
* **Funcionalidad:**
    * Analizar una ventana de tiempo hacia atrás (10 a 15 días).
    * Generar reporte detallado de zonas de acumulación y distribución basadas estrictamente en Bid/Ask.
    * Comparación visual (Walk-Forward) para confirmar reacción del precio.

### Fase 2: Automatización Total
*Versión objetivo: v2.0-alpha*

* **Implementación:** Desarrollo del Robot (Bot) 100% autónomo.
* **Capacidades:**
    * Entra y sale del mercado sin intervención humana.
    * **Auto-mejoramiento:** Capacidad de re-entrenar la red neuronal (handling Concept Drift).

---

## 5. Reglas Críticas de Desarrollo (Mandamientos)

1.  **Modularidad Extrema:** Código organizado en árbol lógico. Prohibido scripts monolíticos.
2.  **Orquestación:** Existencia obligatoria de un archivo principal que coordine módulos.
3.  **Escalabilidad:** Estructura flexible para agregar indicadores sin refactorización masiva.
4.  **Optimización Continua:** Uso obligatorio de `Optuna`.
5.  **Documentación en Código:** *Docstrings* claros.
6.  **Conexión Híbrida:** Producción usa obligatoriamente `MetaTrader5`.
7.  **POLARS OBLIGATORIO:** Se usará siempre `Polars`. **Jamás usar Pandas**.
8.  **INTERFAZ LIMPIA:** No se usarán iconos en las terminales (DOS/Console). Usar librerías de colores de texto.
9.  **RESTRICCIÓN SEVERA DE DATOS (Tics):**
    * **NO usar `Last`:** Viene en 0 o sucio en este broker.
    * **NO usar `Volume` del broker:** Es impreciso. Usar conteo de ticks (Tick Count) propio si es necesario.
    * **NO usar Promedios (MidPrice):** Se prohíbe promediar Bid y Ask.
    * **SOLO usar `Bid`** para detectar ventas (Fuerza Bajista).
    * **SOLO usar `Ask`** para detectar compras (Fuerza Alcista).

---

## 6. Estructura de Archivos Sugerida (Draft)

```text
proyecto_ballenas/
│
├── data/
│   ├── raw/                   # CSVs originales
│   ├── processed/             # CSVs procesados
│   └── models/                # Modelos (.pkl, .h5)
│
├── src/
│   ├── connection/
│   │   └── mt5_connector.py   # Wrapper MT5 (Filtrado estricto Bid/Ask)
│   │
│   ├── features/
│   │   ├── indicators.py      # Indicadores técnicos (Polars)
│   │   ├── tick_processor.py  # Lógica de conteo Bid vs Ask (Sin Last/Vol)
│   │   └── regimes.py         # Uso de regímenes pre-calculados
│   │
│   ├── models/
│   │   ├── clustering.py      # K-Means / DBSCAN
│   │   ├── hybrid_nn.py       # Arquitectura CNN-GRU-Attention
│   │   └── optimizer.py       # Optuna
│   │
│   ├── strategies/
│   │   └── whale_detector.py  # Detección de Transición (Flip Signals)
│   │
│   └── utils/
│       └── logger.py          # Logs y Alertas (Beep/Msg)
│
├── main_monitor_v1.py         # Orquestador Etapa 1
├── requirements.txt           # Dependencias
└── CONTEXTO.md                # Este archivo
