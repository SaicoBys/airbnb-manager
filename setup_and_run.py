#!/usr/bin/env python3

import os
import sys
import subprocess

print("🚀 Airbnb Manager v3.0 - Setup y Verificación")
print("=" * 50)

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

def check_python_version():
    """Verifica la versión de Python"""
    version = sys.version_info
    print(f"\n🐍 Python {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("⚠️  Se recomienda Python 3.8 o superior")
        return False
    
    print("✅ Versión de Python compatible")
    return True

def main():
    # 1. Verificar Python
    if not check_python_version():
        return
    
    # 2. Verificar si estamos en el directorio correcto
    if not os.path.exists('run.py'):
        print("\n❌ No se encontró run.py - verifica que estés en el directorio correcto")
        return
    
    print("\n✅ Directorio correcto detectado")
    
    # 3. Verificar/instalar dependencias
    print("\n🔍 Verificando dependencias...")
    
    # Intentar importar Flask
    try:
        import flask
        print("✅ Flask ya está instalado")
    except ImportError:
        print("❌ Flask no está instalado")
        if input("¿Instalar dependencias? (y/n): ").lower() == 'y':
            run_command("pip3 install -r requirements.txt", "Instalando dependencias")
    
    # 4. Verificar base de datos
    print("\n🗄️  Verificando base de datos...")
    db_path = 'instance/app.db'
    
    if os.path.exists(db_path):
        print("✅ Base de datos encontrada")
    else:
        print("❌ Base de datos no encontrada")
        if input("¿Crear base de datos? (y/n): ").lower() == 'y':
            os.makedirs('instance', exist_ok=True)
            run_command("flask db upgrade", "Creando base de datos")
            run_command("flask seed-db", "Poblando con datos de prueba")
    
    # 5. Verificar archivos críticos
    print("\n📁 Verificando archivos críticos...")
    critical_files = [
        'app/__init__.py',
        'app/templates/base.html', 
        'app/templates/control_panel.html',
        'app/templates/components/intelligent_booking_widget.html'
    ]
    
    all_files_ok = True
    for file_path in critical_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path}")
            all_files_ok = False
    
    if not all_files_ok:
        print("\n❌ Algunos archivos críticos faltan")
        return
    
    # 6. Informar cómo ejecutar
    print("\n" + "=" * 50)
    print("🎉 VERIFICACIÓN COMPLETA")
    print("=" * 50)
    
    print("\n📋 Para iniciar la aplicación:")
    print("   python3 run.py")
    print("\n🌐 Luego abre en tu navegador:")
    print("   http://localhost:5004")
    
    print("\n👤 Usuarios de prueba (si ejecutaste seed-db):")
    print("   Usuario: jacob    | Contraseña: clave123  | Rol: Dueño")
    print("   Usuario: elizabeth| Contraseña: clave123  | Rol: Socia")
    print("   Usuario: alejandrina| Contraseña: clave123| Rol: Empleada")
    
    print("\n🆘 Si hay problemas:")
    print("   1. Verifica los mensajes de error en la consola")
    print("   2. Asegúrate de que todas las dependencias estén instaladas")
    print("   3. Verifica que el puerto 5004 no esté en uso")
    
    if input("\n¿Iniciar la aplicación ahora? (y/n): ").lower() == 'y':
        print("\n🚀 Iniciando Airbnb Manager v3.0...")
        os.system("python3 run.py")

if __name__ == "__main__":
    main()