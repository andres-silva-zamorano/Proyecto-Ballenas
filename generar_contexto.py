import os

# --- CONFIGURACIÓN ---
OUTPUT_FILE = "_CONTEXTO_PROYECTO.txt"
IGNORE_DIRS = {'.git', '__pycache__', 'venv', 'env', '.idea', '.vscode'}
THIS_SCRIPT = os.path.basename(__file__)

def generar_resumen():
    root_dir = os.getcwd()
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as outfile:
        outfile.write(f"=== RESUMEN DE CÓDIGO DEL PROYECTO ===\n")
        outfile.write(f"Generado el: {os.path.basename(root_dir)}\n")
        outfile.write("="*50 + "\n\n")

        file_count = 0
        
        for root, dirs, files in os.walk(root_dir):
            # Filtrar carpetas ignoradas para no entrar en ellas
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            
            for file in files:
                if file.endswith(".py") and file != THIS_SCRIPT:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, root_dir)
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                        # Escribir cabecera del archivo
                        outfile.write(f"\n{'='*20} INICIO ARCHIVO: {rel_path} {'='*20}\n")
                        outfile.write(content)
                        outfile.write(f"\n{'='*20} FIN ARCHIVO: {rel_path} {'='*20}\n\n")
                        
                        print(f"Agregado: {rel_path}")
                        file_count += 1
                        
                    except Exception as e:
                        print(f"Error leyendo {rel_path}: {e}")

    print(f"\n✅ ¡Listo! Se han recopilado {file_count} archivos Python en '{OUTPUT_FILE}'.")
    print("Sube ese archivo al chat para actualizar mi memoria.")

if __name__ == "__main__":
    generar_resumen()
    