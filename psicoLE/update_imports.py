import os
import re

# Directorio donde están los archivos a modificar
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Patrón para buscar la importación antigua
OLD_IMPORT = r'from\s+psicoLE\.database\s+import\s+db\b'

# Función para actualizar un archivo
def update_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Reemplazar la importación
        new_content = re.sub(OLD_IMPORT, 'from database import db', content)
        
        # Solo escribir si hay cambios
        if new_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f'Actualizado: {filepath}')
            return True
        return False
    except Exception as e:
        print(f'Error al procesar {filepath}: {str(e)}')
        return False

# Buscar y actualizar archivos .py
updated_count = 0
for root, _, files in os.walk(BASE_DIR):
    for file in files:
        if file.endswith('.py') and file != 'update_imports.py':
            filepath = os.path.join(root, file)
            if update_file(filepath):
                updated_count += 1

print(f'\nProceso completado. Se actualizaron {updated_count} archivos.')
