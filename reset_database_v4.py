#!/usr/bin/env python3

"""
AIRBNB MANAGER V4.0 - SCRIPT DE RESET COMPLETO DE BASE DE DATOS
Este script elimina las migraciones existentes y crea una base de datos limpia
con la nueva estructura corregida.
"""

import os
import sys
import shutil
import subprocess

def run_command(command, description):
    """Ejecuta un comando y maneja errores"""
    print(f"\n📋 {description}")
    print(f"💻 Ejecutando: {command}")
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Éxito")
            if result.stdout.strip():
                print(f"📤 Salida: {result.stdout.strip()}")
            return True
        else:
            print("❌ Error")
            if result.stderr.strip():
                print(f"📥 Error: {result.stderr.strip()}")
            return False
            
    except Exception as e:
        print(f"❌ Excepción: {e}")
        return False

def main():
    print("🚀 AIRBNB MANAGER V4.0 - RESET DE BASE DE DATOS")
    print("=" * 60)
    print("⚠️  ADVERTENCIA: Este proceso eliminará TODOS los datos existentes")
    print("📋 Se recreará la base de datos con la nueva estructura Queen/King")
    
    response = input("\n¿Continuar? (y/N): ")
    if response.lower() != 'y':
        print("❌ Operación cancelada")
        return
    
    # 1. Eliminar base de datos existente
    print("\n🗄️  PASO 1: Eliminando base de datos existente...")
    db_path = 'instance/app.db'
    if os.path.exists(db_path):
        os.remove(db_path)
        print("✅ Base de datos eliminada")
    else:
        print("ℹ️  No había base de datos existente")
    
    # 2. Eliminar migraciones existentes
    print("\n📁 PASO 2: Eliminando migraciones existentes...")
    migrations_path = 'migrations'
    if os.path.exists(migrations_path):
        shutil.rmtree(migrations_path)
        print("✅ Migraciones eliminadas")
    else:
        print("ℹ️  No había migraciones existentes")
    
    # 3. Inicializar migraciones
    print("\n🔧 PASO 3: Inicializando sistema de migraciones...")
    if not run_command("flask db init", "Inicializando Flask-Migrate"):
        print("❌ Error al inicializar migraciones")
        return
    
    # 4. Crear migración inicial
    print("\n📝 PASO 4: Creando migración inicial...")
    if not run_command('flask db migrate -m "Initial migration v4.0 with Queen/King hierarchy"', 
                      "Creando migración inicial"):
        print("❌ Error al crear migración")
        return
    
    # 5. Aplicar migración
    print("\n⚡ PASO 5: Aplicando migración...")
    if not run_command("flask db upgrade", "Aplicando migración"):
        print("❌ Error al aplicar migración")
        return
    
    # 6. Poblar con datos de prueba
    print("\n🌱 PASO 6: Poblando con datos de prueba...")
    if not run_command("flask seed-db", "Ejecutando seed de datos"):
        print("❌ Error al poblar datos")
        return
    
    print("\n" + "=" * 60)
    print("🎉 ¡RESET COMPLETADO EXITOSAMENTE!")
    print("=" * 60)
    
    print("\n✅ Nueva estructura de base de datos creada:")
    print("   - Jerarquía de habitaciones: Queen 👸 / King 👑")
    print("   - Tabla de paquetes de suministros corregida")
    print("   - Datos de prueba cargados")
    
    print("\n🚀 Para iniciar la aplicación:")
    print("   python3 run.py")
    
    print("\n👤 Usuarios de prueba disponibles:")
    print("   - jacob / clave123 (Dueño)")
    print("   - elizabeth / clave123 (Socia)")
    print("   - alejandrina / clave123 (Empleada)")
    
    print("\n🆘 Si hay problemas:")
    print("   1. Verifica que todas las dependencias estén instaladas")
    print("   2. Asegúrate de estar en el directorio correcto del proyecto")
    print("   3. Verifica que no haya otro proceso usando la base de datos")

if __name__ == "__main__":
    main()