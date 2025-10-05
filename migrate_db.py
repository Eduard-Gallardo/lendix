#!/usr/bin/env python3
"""
Script para migrar la base de datos de Lendix
Corrige inconsistencias en la estructura de la base de datos
"""

import sys
import os

# Agregar el directorio raíz al path para importar los módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.db import init_db, migrar_base_datos, crear_admin_inicial

def main():
    """Ejecuta la migración de la base de datos"""
    print("Iniciando migración de la base de datos...")
    
    try:
        # Inicializar la base de datos (crea tablas si no existen)
        print("Inicializando estructura de base de datos...")
        init_db()
        
        # Migrar datos existentes
        print("Migrando datos existentes...")
        migrar_base_datos()
        
        # Crear admin inicial si no existe
        print("Verificando usuario administrador...")
        crear_admin_inicial()
        
        print("Migración completada exitosamente!")
        print("\nResumen de cambios:")
        print("   • Estructura de base de datos actualizada")
        print("   • Campos de estado corregidos")
        print("   • Constrains de validación actualizados")
        print("   • Usuario administrador verificado")
        
    except Exception as e:
        print(f"Error durante la migración: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
