# 🤖 Contexto Completo para Gemini - Airbnb Manager

## 📊 Resumen del Sistema
Sistema Flask de gestión para Airbnb con:
- **Sistema Dual de Gastos**: Separación entre cuadre de caja de empleada vs rentabilidad empresarial
- **Panel de Control Unificado**: Dashboard con 6 pestañas integradas
- **Roles**: empleada (Elizabeth), socia (Alejandrina), dueños (propietarios)
- **Funcionalidades**: Clientes, estancias, gastos, inventario, reportes financieros

## 🏗️ Arquitectura Técnica
- **Framework**: Python Flask con SQLAlchemy ORM
- **Base de Datos**: SQLite con 8 modelos principales
- **Frontend**: Jinja2 templates + CSS modular + JavaScript vanilla
- **Formularios**: WTForms con validación + AJAX sin recargas
- **Autenticación**: Flask-Login with role-based permissions

## 🔑 Problema Principal Resuelto
**Antes**: Gastos de Alejandrina (socia) se restaban del cuadre de Elizabeth (empleada)
**Después**: Sistema dual donde:
- Elizabeth solo entrega dinero descontando SUS gastos
- Rentabilidad empresarial incluye TODOS los gastos del negocio

## 📂 Estructura del Proyecto
```
airbnb_manager/
├── app/
│   ├── models.py           # 8 modelos de BD con lógica dual
│   ├── routes.py           # 50+ rutas + 4 endpoints AJAX
│   ├── forms.py            # Formularios WTForms
│   ├── decorators.py       # Control de acceso por roles
│   ├── static/css/         # CSS modular (8 archivos)
│   └── templates/          # 20+ templates Jinja2
├── migrations/             # 5 migraciones de BD
├── instance/app.db         # BD SQLite con datos de prueba
├── populate_test_data.py   # Script de datos realistas
├── CHANGELOG.md            # Documentación completa
└── run.py                  # Punto de entrada (puerto 5004)
```

## 💾 Modelos de Base de Datos Principales

### User (Usuarios del Sistema)
- roles: 'empleada', 'socia', 'dueño'
- Métodos de autorización y permisos granulares

### Expense (Sistema Dual de Gastos) ⭐
```python
def affects_cash_closure(self):
    """Solo gastos pagados por empleadas afectan cuadre de caja"""
    return self.paid_by and self.paid_by.is_employee()

def affects_business_profitability(self):
    """TODOS los gastos afectan rentabilidad empresarial"""
    return True
```

### Client, Stay, Payment, Supply, CashClosure, EmployeeDelivery
- Relaciones completas entre entidades
- Métodos de cálculo financiero integrados

## 🎛️ Panel de Control Unificado (control_panel.html)
6 pestañas principales:
1. **📊 Resumen**: Estadísticas + acciones rápidas + alertas
2. **👥 Clientes**: Lista + formulario AJAX
3. **🏨 Estancias**: Reservas + check-ins/outs
4. **💸 Gastos**: Sistema dual con indicadores visuales
5. **📦 Inventario**: Stock + alertas de reposición
6. **💰 Finanzas**: Análisis Elizabeth vs rentabilidad empresarial

## 🛣️ Rutas Principales

### Panel Unificado
- `GET /` → Panel principal con 6 pestañas

### Endpoints AJAX (Nuevos)
- `POST /ajax/add_client` → Crear cliente sin recargar
- `POST /ajax/add_stay` → Registrar estancia instantáneamente
- `POST /ajax/add_expense` → Controlar gastos en tiempo real
- `POST /ajax/update_stock` → Actualizar inventario al momento

### Análisis Financiero
- `GET /reports` → Reportes con sistema dual
- `GET /monthly_report` → Cierre mensual Elizabeth vs negocio

## 🎨 CSS Modular
```css
main.css {
  @import base.css;      /* Variables, utilidades */
  @import navbar.css;    /* Navegación */
  @import buttons.css;   /* Elementos interactivos */
  @import forms.css;     /* Formularios + validación */
  @import tables.css;    /* Datos tabulares */
  @import alerts.css;    /* Mensajes */
  @import reports.css;   /* Dashboard */
  @import dashboard.css; /* Panel unificado ⭐ */
}
```

## 🧪 Datos de Prueba
- **20 clientes** con nombres dominicanos
- **18 gastos** que demuestran sistema dual:
  - Elizabeth: DOP 2,001.25 (afecta cuadre)
  - Alejandrina: DOP 25,790.00 (no afecta cuadre)
  - Propietarios: DOP 43,800.00 (no afecta cuadre)
- **26 estancias** y **47 pagos** con datos realistas
- **21 productos** de inventario (3 con stock bajo)

## 🔐 Sistema de Permisos
```python
@login_required                    # Autenticación básica
@permission_required('function')   # Permisos granulares
@role_required('role')            # Control por rol
@owner_required                   # Solo propietarios
@management_required              # Gerencia (socia + dueños)
```

## ⚙️ Configuración Actual
- **Puerto**: 5004 (cambiado por conflictos)
- **Debug**: Activado para desarrollo
- **BD**: SQLite en `/instance/app.db`
- **Credenciales de prueba**:
  - elizabeth / password123 (empleada)
  - alejandrina / password123 (socia)
  - propietario1 / password123 (dueño)

## 💡 Características Destacadas
1. **Sistema Dual Financiero**: Cuadre justo para Elizabeth + rentabilidad real para propietarios
2. **Panel Unificado**: Todo en una página con pestañas
3. **Formularios AJAX**: Sin recargas, validación en tiempo real
4. **CSS Modular**: Mantenimiento simplificado
5. **Responsive Design**: Funciona en móviles y desktop
6. **Alertas Contextuales**: Stock bajo, gastos pendientes
7. **Datos Realistas**: Listo para demos y pruebas

## 🎯 Flujos de Trabajo Principales

### Flujo de Gastos (Dual System)
1. Usuario selecciona "quién pagó" el gasto
2. Sistema determina automáticamente:
   - Si afecta cuadre de Elizabeth: `affects_cash_closure()`
   - Si afecta rentabilidad: `affects_business_profitability()`
3. Indicadores visuales muestran impacto en tiempo real

### Flujo del Panel de Control
1. Login → Dashboard unificado
2. Navegación por pestañas instantánea
3. Formularios AJAX en cada sección
4. Alertas y notificaciones contextuales
5. Estadísticas actualizadas dinámicamente

## 🚀 Estado Actual
✅ **Sistema Completamente Funcional**
✅ **Panel Unificado Implementado**
✅ **Sistema Dual de Gastos Operativo**
✅ **CSS Modular Establecido**
✅ **Datos de Prueba Poblados**
✅ **Errores Técnicos Resueltos**

**El sistema está listo para producción y preparado para escalar.**

---

*Para contexto técnico específico, consultar también:*
- `CHANGELOG.md` → Documentación completa de cambios
- `app/models.py` → Lógica de negocio y BD
- `app/routes.py` → Endpoints y lógica de rutas
- `app/templates/control_panel.html` → Panel unificado
- `app/static/css/` → Arquitectura CSS modular