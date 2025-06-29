#!/usr/bin/env python3

import os
import sqlite3

# Verificar si la base de datos existe
db_path = '/Users/saicobys/Developer/airbnb_manager/instance/app.db'

if os.path.exists(db_path):
    print("✅ Base de datos encontrada en:", db_path)
    
    try:
        # Conectar a la base de datos
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Obtener lista de tablas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print(f"📋 Encontradas {len(tables)} tablas:")
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"   - {table_name}: {count} registros")
        
        # Verificar si hay usuarios
        cursor.execute("SELECT COUNT(*) FROM user")
        user_count = cursor.fetchone()[0]
        
        if user_count > 0:
            print("✅ La base de datos tiene usuarios registrados")
        else:
            print("⚠️  No hay usuarios en la base de datos")
            print("💡 Ejecuta: flask seed-db para crear datos de prueba")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error al verificar la base de datos: {e}")
        
else:
    print("❌ Base de datos no encontrada en:", db_path)
    print("💡 Ejecuta: flask db upgrade para crear la base de datos")
    
print("\n🔧 Comandos útiles:")
print("   flask db upgrade    # Crear/actualizar base de datos")
print("   flask seed-db       # Poblar con datos de prueba")
print("   python3 run.py      # Iniciar aplicación")