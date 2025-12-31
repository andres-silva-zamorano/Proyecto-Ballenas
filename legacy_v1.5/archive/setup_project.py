import os

def create_structure():
    # Estructura basada en la especificación
    paths = [
        "data/raw",
        "data/processed",
        "data/models",
        "src/connection",
        "src/features",
        "src/models",
        "src/strategies",
        "src/utils"
    ]

    # Archivos base vacíos para iniciar (modules)
    files = [
        "src/connection/mt5_connector.py",
        "src/features/indicators.py",
        "src/features/tick_processor.py",
        "src/features/regimes.py",
        "src/models/clustering.py",
        "src/models/hybrid_nn.py",
        "src/models/optimizer.py",
        "src/strategies/whale_detector.py",
        "src/utils/logger.py",
        "main_monitor_v1.py",
        "requirements.txt",
        "CONTEXTO.md"
    ]

    print("--- INICIANDO PROTOCOLO DE CREACIÓN [PROYECTO BALLENAS] ---")
    
    for path in paths:
        if not os.path.exists(path):
            os.makedirs(path)
            print(f"[OK] Directorio creado: {path}")
        else:
            print(f"[SKIP] Directorio ya existe: {path}")

    for file in files:
        if not os.path.exists(file):
            with open(file, 'w') as f:
                pass # Crear archivo vacío
            print(f"[OK] Archivo creado: {file}")
        else:
            print(f"[SKIP] Archivo ya existe: {file}")
            
    print("--- ESTRUCTURA FINALIZADA ---")

if __name__ == "__main__":
    create_structure()