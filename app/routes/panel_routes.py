"""
AIRBNB MANAGER V3.0 - RUTAS DEL PANEL DE CONTROL
Contiene las rutas principales del dashboard y panel de control unificado
"""

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from sqlalchemy import func
from datetime import datetime

from app.extensions import db
from app.models import DashboardStats, Client, Stay, Room, Supply, Payment, Expense
from app.decorators import permission_required

bp = Blueprint('panel', __name__)

# =====================================================================
# RUTA PRINCIPAL (PANEL DE CONTROL UNIFICADO)
# =====================================================================

@bp.route('/')
@bp.route('/index')
@login_required
def index():
    """Panel de Control Unificado v3.0 - Lógica de negocio centralizada en modelos"""
    # Obtener todas las estadísticas desde la clase centralizada
    stats = DashboardStats.get_panel_statistics()
    
    return render_template('control_panel.html', 
                         title='Panel de Control',
                         **stats)

# =====================================================================
# RUTAS DE REPORTES Y ANÁLISIS
# =====================================================================

@bp.route('/reports')
@login_required
@permission_required('can_view_reports')
def reports():
    """Reporte financiero completo con gráficos e análisis"""
    from calendar import monthrange
    from datetime import datetime
    from sqlalchemy import extract
    from flask import current_app
    
    total_income_dop = db.session.query(func.sum(Payment.amount)).scalar() or 0.0
    total_expenses_dop = db.session.query(func.sum(Expense.amount)).scalar() or 0.0
    profit_dop = total_income_dop - total_expenses_dop
    
    exchange_rate = current_app.config.get('TASA_CAMBIO_DOP_USD', 1.0)
    total_income_usd = total_income_dop / exchange_rate if exchange_rate > 0 else 0
    total_expenses_usd = total_expenses_dop / exchange_rate if exchange_rate > 0 else 0
    profit_usd = profit_dop / exchange_rate if exchange_rate > 0 else 0

    # Ingresos por habitación
    income_by_room_query = db.session.query(
        Room.name, 
        func.sum(Payment.amount).label('total_generated')
    ).select_from(Payment).join(Stay).join(Room)\
     .group_by(Room.name).order_by(func.sum(Payment.amount).desc()).all()
    
    income_chart_labels = [row.name for row in income_by_room_query]
    income_chart_data = [row.total_generated for row in income_by_room_query]

    # Gastos por categoría
    expenses_by_category_query = db.session.query(
        Expense.category, 
        func.sum(Expense.amount).label('total_spent')
    ).group_by(Expense.category).order_by(func.sum(Expense.amount).desc()).all()
    
    expense_chart_labels = [row.category for row in expenses_by_category_query]
    expense_chart_data = [row.total_spent for row in expenses_by_category_query]

    # Datos mensuales del año actual
    current_year = datetime.utcnow().year
    monthly_labels = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", 
                     "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    
    income_by_month_query = db.session.query(
        extract('month', Payment.payment_date).label('month'), 
        func.sum(Payment.amount)
    ).filter(extract('year', Payment.payment_date) == current_year)\
     .group_by('month').all()
    
    monthly_income_data = [0] * 12
    for row in income_by_month_query: 
        monthly_income_data[row.month - 1] = row[1]

    expense_by_month_query = db.session.query(
        extract('month', Expense.expense_date).label('month'), 
        func.sum(Expense.amount)
    ).filter(extract('year', Expense.expense_date) == current_year)\
     .group_by('month').all()
    
    monthly_expense_data = [0] * 12
    for row in expense_by_month_query: 
        monthly_expense_data[row.month - 1] = row[1]

    monthly_profit_data = [(inc - exp) for inc, exp in zip(monthly_income_data, monthly_expense_data)]
    
    # Frecuencia de clientes
    client_frequency = db.session.query(
        Client.full_name, 
        func.count(Stay.id).label('stay_count')
    ).join(Stay).group_by(Client.full_name)\
     .order_by(func.count(Stay.id).desc()).all()

    return render_template('reports.html', 
        title='Reporte Financiero',
        total_income_dop=total_income_dop,
        total_expenses_dop=total_expenses_dop,
        profit_dop=profit_dop,
        total_income_usd=total_income_usd,
        total_expenses_usd=total_expenses_usd,
        profit_usd=profit_usd,
        income_by_room=income_by_room_query,
        income_chart_labels=income_chart_labels,
        income_chart_data=income_chart_data,
        expense_chart_labels=expense_chart_labels,
        expense_chart_data=expense_chart_data,
        monthly_labels=monthly_labels,
        monthly_income_data=monthly_income_data,
        monthly_expense_data=monthly_expense_data,
        monthly_profit_data=monthly_profit_data,
        client_frequency=client_frequency
    )

@bp.route('/monthly_report')
@login_required
@permission_required('can_view_monthly_report')
def monthly_report():
    """Reporte mensual detallado con análisis de gastos"""
    from calendar import monthrange
    from flask import current_app
    
    year = datetime.utcnow().year
    month = datetime.utcnow().month
    start_date = datetime(year, month, 1)
    end_date = datetime(year, month, monthrange(year, month)[1], 23, 59, 59)

    incomes = Payment.query.filter(
        Payment.payment_date >= start_date, 
        Payment.payment_date <= end_date
    ).order_by(Payment.payment_date.desc()).all()
    
    expenses = Expense.query.filter(
        Expense.expense_date >= start_date, 
        Expense.expense_date <= end_date
    ).order_by(Expense.expense_date.desc()).all()
    
    employee_expenses = [e for e in expenses if e.affects_cash_closure()]

    total_income_dop = sum(p.amount for p in incomes)
    total_expenses_dop = sum(e.amount for e in employee_expenses)
    profit_dop = total_income_dop - total_expenses_dop

    exchange_rate = current_app.config.get('TASA_CAMBIO_DOP_USD', 1.0)
    total_income_usd = total_income_dop / exchange_rate if exchange_rate > 0 else 0
    total_expenses_usd = total_expenses_dop / exchange_rate if exchange_rate > 0 else 0
    profit_usd = total_income_usd - total_expenses_usd
    
    total_all_expenses_dop = sum(e.amount for e in expenses)
    
    return render_template(
        'monthly_report.html',
        title='Reporte de Cierre de Mes',
        incomes=incomes,
        expenses=expenses,
        employee_expenses=employee_expenses,
        total_income_dop=total_income_dop,
        total_expenses_dop=total_expenses_dop,
        total_all_expenses_dop=total_all_expenses_dop,
        profit_dop=profit_dop,
        total_income_usd=total_income_usd,
        total_expenses_usd=total_expenses_usd,
        profit_usd=profit_usd,
        report_month=start_date.strftime('%B %Y')
    )