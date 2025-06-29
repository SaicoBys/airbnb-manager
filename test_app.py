#!/usr/bin/env python3

import os
import sys

# Agregar el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    print("🔍 Verificando importaciones...")
    
    # Test 1: Importar configuración
    print("1. Importando config...")
    from config import Config
    print("   ✅ Config importado correctamente")
    
    # Test 2: Importar extensiones
    print("2. Importando extensiones...")
    from app.extensions import db
    print("   ✅ Extensiones importadas correctamente")
    
    # Test 3: Importar modelos
    print("3. Importando modelos...")
    from app.models import User, Room, Stay
    print("   ✅ Modelos importados correctamente")
    
    # Test 4: Importar blueprints individualmente
    print("4. Importando blueprints...")
    from app.routes.panel_routes import bp as panel_bp
    print("   ✅ Panel routes importado")
    
    from app.routes.auth_routes import bp as auth_bp
    print("   ✅ Auth routes importado")
    
    from app.routes.supply_routes import bp as supply_bp
    print("   ✅ Supply routes importado")
    
    from app.routes.ajax_routes import bp as ajax_bp
    print("   ✅ Ajax routes importado")
    
    from app.routes.intelligence_routes import bp as intelligence_bp
    print("   ✅ Intelligence routes importado")
    
    # Test 5: Importar función de registro de blueprints
    print("5. Importando register_blueprints...")
    from app.routes import register_blueprints
    print("   ✅ register_blueprints importado")
    
    # Test 6: Crear la aplicación
    print("6. Creando aplicación...")
    from app import create_app
    app = create_app()
    print("   ✅ Aplicación creada correctamente")
    
    # Test 7: Verificar rutas registradas
    print("7. Verificando rutas registradas...")
    with app.app_context():
        rules = list(app.url_map.iter_rules())
        print(f"   ✅ {len(rules)} rutas registradas")
        
        # Mostrar algunas rutas importantes
        important_routes = ['/', '/auth/login', '/auth/logout', '/supply-packages/', '/intelligence/suggest_availability']
        for route in important_routes:
            found = any(str(rule) == route for rule in rules)
            status = "✅" if found else "❌"
            print(f"   {status} Ruta {route}: {'Encontrada' if found else 'NO ENCONTRADA'}")
    
    print("\n🎉 ¡Todas las verificaciones pasaron! La aplicación debería funcionar correctamente.")
    print("\n📝 Para iniciar la aplicación:")
    print("   python3 run.py")
    
except ImportError as e:
    print(f"❌ Error de importación: {e}")
    print("💡 Verifica que todas las dependencias estén instaladas.")
    sys.exit(1)
    
except Exception as e:
    print(f"❌ Error inesperado: {e}")
    print(f"📍 Tipo de error: {type(e).__name__}")
    import traceback
    print("📋 Traceback completo:")
    traceback.print_exc()
    sys.exit(1)