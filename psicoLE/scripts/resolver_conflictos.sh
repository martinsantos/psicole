#!/bin/bash

# Script para resolver conflictos de fusión en el proyecto PsicoLE
# Creado: $(date)


# Función para mostrar ayuda
mostrar_ayuda() {
    echo "Uso: $0 [OPCION]"
    echo "Resuelve conflictos de fusión en el proyecto PsicoLE"
    echo ""
    echo "Opciones:"
    echo "  -h, --help    Muestra esta ayuda"
    echo "  -a, --all     Resuelve todos los conflictos automáticamente (mantiene los cambios locales)"
    echo "  -m, --manual  Muestra los archivos con conflictos para resolver manualmente"
    echo ""
}

# Función para resolver conflictos automáticamente (manteniendo cambios locales)
resolver_automatico() {
    echo "[INFO] Resolviendo conflictos automáticamente (manteniendo cambios locales)..."
    
    # Lista de archivos con conflictos
    archivos_conflicto=$(grep -l "<<<<<<< HEAD" --include="*.py" --include="*.html" -r .)
    
    for archivo in $archivos_conflicto; do
        echo "Procesando: $archivo"
        
        # Crear copia de seguridad
        cp "$archivo" "${archivo}.backup_$(date +%Y%m%d_%H%M%S)"
        
        # Resolver conflicto manteniendo cambios locales (HEAD)
        awk '/<<<<<<</ {skip=1; next} /=======/ {skip=0; next} />>>>>>>/ {next} {if (!skip) print}' "$archivo" > "${archivo}.tmp"
        
        # Mover el archivo temporal al original
        mv "${archivo}.tmp" "$archivo"
    done
    
    echo "[INFO] Proceso de resolución automática completado."
    echo "[INFO] Se han creado copias de seguridad de los archivos originales."
}

# Función para mostrar archivos con conflictos
mostrar_conflictos() {
    echo "[INFO] Archivos con conflictos de fusión:"
    echo "----------------------------------------"
    grep -l "<<<<<<< HEAD" --include="*.py" --include="*.html" -r . | while read -r archivo; do
        echo "- $archivo"
    done
    echo ""
    echo "[INFO] Para resolver manualmente, edite los archivos y elimine las marcas de conflicto."
    echo "       Las marcas de conflicto son:"
    echo "       <<<<<<< HEAD (tus cambios)"
    echo "       ======= (separador)"
    echo "       >>>>>>> hash (cambios de la otra rama)"
}

# Procesar argumentos
case "$1" in
    -h|--help)
        mostrar_ayuda
        exit 0
        ;;
    -a|--all)
        resolver_automatico
        exit 0
        ;;
    -m|--manual)
        mostrar_conflictos
        exit 0
        ;;
    *)
        echo "Error: Argumento no reconocido"
        echo "Use $0 --help para ver las opciones disponibles"
        exit 1
        ;;
esac

# Si no se proporcionaron argumentos, mostrar ayuda
mostrar_ayuda
exit 0
