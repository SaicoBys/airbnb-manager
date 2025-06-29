#!/usr/bin/env python3

# Test mínimo para verificar problemas específicos
import os
import sys

# Simular la estructura básica sin importar Flask
print("🔍 Verificando problemas potenciales...")

# 1. Verificar archivos críticos
critical_files = [
    'app/__init__.py',
    'app/routes/__init__.py', 
    'app/routes/panel_routes.py',
    'app/templates/base.html',
    'app/templates/control_panel.html',
    'app/templates/components/intelligent_booking_widget.html',
    'app/templates/_macros.html',
    'config.py',
    'run.py'
]

missing_files = []
for file_path in critical_files:
    if not os.path.exists(file_path):
        missing_files.append(file_path)
    else:
        print(f"✅ {file_path}")

if missing_files:
    print("\n❌ Archivos faltantes:")
    for file in missing_files:
        print(f"   - {file}")
else:
    print("\n✅ Todos los archivos críticos están presentes")

# 2. Verificar template del widget inteligente
print("\n🔍 Verificando template del widget inteligente...")
widget_path = 'app/templates/components/intelligent_booking_widget.html'

if os.path.exists(widget_path):
    with open(widget_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Verificar estructura Jinja2
    issues = []
    
    if '{% call render_widget(' not in content:
        issues.append("Falta {% call render_widget( ... ) %}")
    
    if '{% endcall %}' not in content:
        issues.append("Falta {% endcall %}")
        
    if '{% from "_macros.html" import' not in content:
        issues.append("Falta importación de macros")
    
    if issues:
        print("❌ Problemas encontrados en el widget:")
        for issue in issues:
            print(f"   - {issue}")
    else:
        print("✅ Estructura del widget correcta")

# 3. Verificar archivo de macros
print("\n🔍 Verificando macros...")
macros_path = 'app/templates/_macros.html'

if os.path.exists(macros_path):
    with open(macros_path, 'r', encoding='utf-8') as f:
        macros_content = f.read()
    
    required_macros = ['render_widget', 'render_form_field', 'render_button', 'render_alert', 'render_loading']
    missing_macros = []
    
    for macro in required_macros:
        if f'macro {macro}(' not in macros_content:
            missing_macros.append(macro)
    
    if missing_macros:
        print("❌ Macros faltantes:")
        for macro in missing_macros:
            print(f"   - {macro}")
    else:
        print("✅ Todos los macros requeridos están presentes")

print("\n📋 Resumen de verificación:")
print("   - Archivos críticos: ✅" if not missing_files else "   - Archivos críticos: ❌")
print("   - Widget inteligente: ✅" if not issues else "   - Widget inteligente: ❌")
print("   - Macros: ✅" if not missing_macros else "   - Macros: ❌")

print("\n💡 Si todo está ✅ pero la página no carga:")
print("   1. Verifica que Flask esté instalado: pip install flask")
print("   2. Inicia la aplicación: python3 run.py")
print("   3. Abre http://localhost:5004 en tu navegador")
print("   4. Revisa la consola para errores específicos")