"""
AIRBNB MANAGER V3.0 - RUTAS DE AUTENTICACIÓN Y GESTIÓN DE USUARIOS
Contiene las rutas para login, logout y gestión de usuarios del sistema
"""

from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_login import login_user, logout_user, current_user, login_required
from urllib.parse import urlparse

from app.extensions import db
from app.models import User
from app.forms import LoginForm
from app.decorators import role_required, owner_required

bp = Blueprint('auth', __name__)

# =====================================================================
# RUTAS DE AUTENTICACIÓN
# =====================================================================

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Página de inicio de sesión"""
    if current_user.is_authenticated:
        return redirect(url_for('panel.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user is None or not user.check_password(form.password.data):
            flash('Usuario o contraseña incorrectos', 'error')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=form.remember_me.data)
        flash(f'Bienvenido/a, {user.get_display_name()}!', 'success')
        
        # Redirigir a la página solicitada o al panel principal
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            next_page = url_for('panel.index')
        
        return redirect(next_page)
    
    return render_template('auth/login.html', title='Iniciar Sesión', form=form)

@bp.route('/logout')
@login_required
def logout():
    """Cerrar sesión del usuario"""
    flash(f'Sesión cerrada correctamente. ¡Hasta luego, {current_user.get_display_name()}!', 'info')
    logout_user()
    return redirect(url_for('auth.login'))

# =====================================================================
# RUTAS DE GESTIÓN DE USUARIOS (Solo para dueños)
# =====================================================================

@bp.route('/users')
@login_required
@owner_required
def manage_users():
    """Panel de gestión de usuarios (solo dueños)"""
    users = User.query.order_by(User.username).all()
    return render_template('auth/manage_users.html', 
                         title='Gestión de Usuarios', 
                         users=users)

@bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@owner_required
def create_user():
    """Crear nuevo usuario"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        role = request.form.get('role', '').strip()
        
        # Validaciones
        if not username or not password or not role:
            flash('Todos los campos son requeridos', 'error')
            return redirect(url_for('auth.create_user'))
        
        if User.query.filter_by(username=username).first():
            flash('El nombre de usuario ya existe', 'error')
            return redirect(url_for('auth.create_user'))
        
        if role not in ['dueño', 'socia', 'empleada']:
            flash('Rol inválido', 'error')
            return redirect(url_for('auth.create_user'))
        
        # Crear usuario
        try:
            user = User(username=username, role=role)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            
            flash(f'Usuario {username} creado exitosamente como {role}', 'success')
            return redirect(url_for('auth.manage_users'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear usuario: {str(e)}', 'error')
    
    return render_template('auth/create_user.html', title='Crear Usuario')

@bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@owner_required
def edit_user(user_id):
    """Editar usuario existente"""
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        role = request.form.get('role', '').strip()
        new_password = request.form.get('new_password', '').strip()
        
        # Validaciones
        if not username or not role:
            flash('Username y rol son requeridos', 'error')
            return redirect(url_for('auth.edit_user', user_id=user_id))
        
        # Verificar si el username ya existe (excepto para el usuario actual)
        existing_user = User.query.filter_by(username=username).first()
        if existing_user and existing_user.id != user.id:
            flash('El nombre de usuario ya existe', 'error')
            return redirect(url_for('auth.edit_user', user_id=user_id))
        
        if role not in ['dueño', 'socia', 'empleada']:
            flash('Rol inválido', 'error')
            return redirect(url_for('auth.edit_user', user_id=user_id))
        
        # Actualizar usuario
        try:
            user.username = username
            user.role = role
            
            if new_password:
                user.set_password(new_password)
            
            db.session.commit()
            flash(f'Usuario {username} actualizado exitosamente', 'success')
            return redirect(url_for('auth.manage_users'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar usuario: {str(e)}', 'error')
    
    return render_template('auth/edit_user.html', 
                         title='Editar Usuario', 
                         user=user)

@bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@owner_required
def delete_user(user_id):
    """Eliminar usuario"""
    user = User.query.get_or_404(user_id)
    
    # No permitir que el dueño se elimine a sí mismo
    if user.id == current_user.id:
        flash('No puedes eliminar tu propia cuenta', 'error')
        return redirect(url_for('auth.manage_users'))
    
    # Verificar si el usuario tiene datos asociados
    if user.expenses_paid.count() > 0 or user.cash_deliveries.count() > 0:
        flash(f'No se puede eliminar {user.username} porque tiene datos asociados', 'warning')
        return redirect(url_for('auth.manage_users'))
    
    try:
        username = user.username
        db.session.delete(user)
        db.session.commit()
        flash(f'Usuario {username} eliminado exitosamente', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar usuario: {str(e)}', 'error')
    
    return redirect(url_for('auth.manage_users'))

@bp.route('/profile')
@login_required
def profile():
    """Perfil del usuario actual"""
    return render_template('auth/profile.html', 
                         title='Mi Perfil', 
                         user=current_user)

@bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Cambiar contraseña del usuario actual"""
    if request.method == 'POST':
        current_password = request.form.get('current_password', '').strip()
        new_password = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        # Validaciones
        if not current_password or not new_password or not confirm_password:
            flash('Todos los campos son requeridos', 'error')
            return redirect(url_for('auth.change_password'))
        
        if not current_user.check_password(current_password):
            flash('La contraseña actual es incorrecta', 'error')
            return redirect(url_for('auth.change_password'))
        
        if new_password != confirm_password:
            flash('Las contraseñas nuevas no coinciden', 'error')
            return redirect(url_for('auth.change_password'))
        
        if len(new_password) < 6:
            flash('La nueva contraseña debe tener al menos 6 caracteres', 'error')
            return redirect(url_for('auth.change_password'))
        
        # Actualizar contraseña
        try:
            current_user.set_password(new_password)
            db.session.commit()
            flash('Contraseña actualizada exitosamente', 'success')
            return redirect(url_for('auth.profile'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar contraseña: {str(e)}', 'error')
    
    return render_template('auth/change_password.html', 
                         title='Cambiar Contraseña')