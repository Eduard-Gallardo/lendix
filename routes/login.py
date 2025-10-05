from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for, session
import sqlite3
from utils.db import get_db_connection
from werkzeug.security import check_password_hash
import re
from datetime import datetime, timedelta

# Configuración del Blueprint
login_bp = Blueprint('login', __name__, template_folder='templates')

# Diccionario para rastrear intentos de login fallidos
login_attempts = {}

def validate_email(email):
    """Valida el formato del email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def is_login_blocked(email):
    """Verifica si el email está bloqueado por intentos fallidos"""
    if email in login_attempts:
        attempts = login_attempts[email]
        if attempts['count'] >= 5:
            # Bloquear por 15 minutos
            if datetime.now() - attempts['last_attempt'] < timedelta(minutes=15):
                return True
            else:
                # Resetear contador después del bloqueo
                del login_attempts[email]
    return False

def record_failed_attempt(email):
    """Registra un intento fallido de login"""
    if email not in login_attempts:
        login_attempts[email] = {'count': 0, 'last_attempt': None}
    
    login_attempts[email]['count'] += 1
    login_attempts[email]['last_attempt'] = datetime.now()

def clear_failed_attempts(email):
    """Limpia los intentos fallidos después de un login exitoso"""
    if email in login_attempts:
        del login_attempts[email]

# Rutas del Blueprint
@login_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Obtener datos del formulario
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        remember_me = request.form.get('remember-me')
        
        # Validar campos obligatorios
        if not email or not password:
            flash('Por favor, complete todos los campos', 'error')
            return render_template('views/login.html')
        
        # Validar formato del email
        if not validate_email(email):
            flash('Por favor, ingrese un email válido', 'error')
            return render_template('views/login.html')
        
        # Verificar si el email está bloqueado
        if is_login_blocked(email):
            flash('Demasiados intentos fallidos. Por favor, espere 15 minutos antes de intentar nuevamente.', 'error')
            return render_template('views/login.html')
        
        # Buscar usuario en la base de datos
        conn = get_db_connection()
        usuario = conn.execute(
            'SELECT * FROM usuarios WHERE email = ?', (email,)
        ).fetchone()
        conn.close()
        
        
        # Verificar si el usuario existe y la contraseña es correcta
        if usuario and check_password_hash(usuario[4], password):
            # Verificar si el usuario está activo (1 = activo, 0 = inactivo)
            if usuario[6] != 1:
                flash('Tu cuenta está pendiente de aprobación por un administrador. Por favor, espera a ser activado.', 'warning')
                return render_template('views/login.html')
            
            # Limpiar intentos fallidos después de login exitoso
            clear_failed_attempts(email)
            
            # Login exitoso - guardar datos en sesión
            session['user_id'] = usuario[0]
            session['user_nombre'] = usuario[1]
            session['user_email'] = usuario[2]
            session['user_telefono'] = usuario[3]
            session['rol'] = usuario[5]
            session['login_time'] = datetime.now().isoformat()
            
            # Configurar sesión persistente si "Recordarme" está marcado
            if remember_me:
                session.permanent = True
            
            flash(f'¡Bienvenido de nuevo, {usuario[1]}!', 'success')
            
            # Redirección según el rol del usuario
            if usuario[5] == 'admin':
                return redirect('/admin')
            else:
                # Instructor y funcionario van al índice
                return redirect('/')
        else:
            # Login fallido - registrar intento
            record_failed_attempt(email)
            
            # Mensaje personalizado según el número de intentos
            attempts_left = 5 - login_attempts.get(email, {}).get('count', 0)
            if attempts_left > 0:
                flash(f'Credenciales incorrectas. Te quedan {attempts_left} intentos.', 'error')
            else:
                flash('Demasiados intentos fallidos. Por favor, espere 15 minutos antes de intentar nuevamente.', 'error')
            
            return render_template('views/login.html')
    
    return render_template('views/login.html')

@login_bp.route('/logout')
def logout():
    # Obtener información del usuario antes de limpiar la sesión
    user_name = session.get('user_nombre', 'Usuario')
    
    # Limpiar la sesión
    session.clear()
    
    flash(f'Has cerrado sesión correctamente, {user_name}', 'success')
    return redirect(url_for('login.login'))

@login_bp.route('/session-info')
def session_info():
    """Endpoint para obtener información de la sesión actual"""
    if 'user_id' not in session:
        return jsonify({'authenticated': False})
    
    return jsonify({
        'authenticated': True,
        'user': {
            'id': session.get('user_id'),
            'nombre': session.get('user_nombre'),
            'email': session.get('user_email'),
            'rol': session.get('rol'),
            'login_time': session.get('login_time')
        }
    })

# Middleware para verificar autenticación
def login_required(view):
    from functools import wraps
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor, inicie sesión para acceder a esta página', 'error')
            return redirect(url_for('login.login'))
        return view(*args, **kwargs)
    return wrapped_view

# Middleware para verificar si el usuario es admin
def admin_required(view):
    from functools import wraps
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor, inicie sesión para acceder a esta página', 'error')
            return redirect(url_for('login.login'))
        if session.get('rol') != 'admin':
            flash('No tienes permisos para acceder a esta página', 'error')
            return redirect('/')
        return view(*args, **kwargs)
    return wrapped_view

# Middleware para verificar si el usuario puede hacer préstamos (instructor o funcionario)
def prestamo_required(view):
    from functools import wraps
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor, inicie sesión para acceder a esta página', 'error')
            return redirect(url_for('login.login'))
        if session.get('rol') not in ['admin', 'instructor', 'funcionario']:
            flash('No tienes permisos para realizar préstamos', 'error')
            return redirect('/')
        return view(*args, **kwargs)
    return wrapped_view

# API endpoint para verificar credenciales
@login_bp.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    email = data.get('email', '')
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({'success': False, 'message': 'Email y contraseña requeridos'}), 400
    
    conn = get_db_connection()
    usuario = conn.execute(
        'SELECT * FROM usuarios WHERE email = ?', (email,)
    ).fetchone()
    conn.close()
    
    if usuario and check_password_hash(usuario[4], password):
        if usuario[6] != 1:
            return jsonify({'success': False, 'message': 'Cuenta pendiente de aprobación'}), 403
            
        return jsonify({
            'success': True, 
            'message': 'Login exitoso',
            'user': {
                'id': usuario[0],
                'nombre': usuario[1],
                'email': usuario[2],
                'rol': usuario[5]
            }
        })
    else:
        return jsonify({'success': False, 'message': 'Credenciales incorrectas'}), 401