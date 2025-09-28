from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for, session
import sqlite3
from utils.db import get_db_connection
from werkzeug.security import check_password_hash

# Configuración del Blueprint
login_bp = Blueprint('login', __name__, template_folder='templates')

# Rutas del Blueprint
@login_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Obtener datos del formulario
        email = request.form.get('email')
        password = request.form.get('password')
        remember_me = request.form.get('remember-me')
        
        # Validar campos obligatorios
        if not email or not password:
            flash('Por favor, complete todos los campos', 'error')
            return render_template('views/login.html')
        
        # Buscar usuario en la base de datos
        conn = get_db_connection()
        usuario = conn.execute(
            'SELECT * FROM usuarios WHERE email = ? AND activo = 1', (email,)
        ).fetchone()
        conn.close()
        
        if usuario and check_password_hash(usuario['password'], password):
            # Login exitoso
            session['user_id'] = usuario['id']
            session['user_nombre'] = usuario['nombre']
            session['user_email'] = usuario['email']
            session['user_telefono'] = usuario['telefono']
            session['rol'] = usuario['rol']  # Usar el rol de la base de datos
            
            # Configurar sesión persistente si "Recordarme" está marcado
            if remember_me:
                session.permanent = True
            
            flash(f'¡Bienvenido de nuevo, {usuario["nombre"]}!', 'success')
            
            # REDIRECCIÓN ESPECÍFICA SEGÚN EL ROL
            if usuario['rol'] == 'admin':
                return redirect(url_for('admin.admin'))
            elif usuario['rol'] == 'instructor':
                return redirect(url_for('instructor.panel_instructor'))
            else:
                # Aprendices y externos van al índice
                return redirect(url_for('index'))
        else:
            # Login fallido
            flash('Credenciales incorrectas. Por favor, intente nuevamente.', 'error')
            return render_template('views/login.html')
    
    return render_template('views/login.html')

@login_bp.route('/logout')
def logout():
    # Limpiar la sesión
    session.clear()
    flash('Has cerrado sesión correctamente', 'success')
    return redirect(url_for('login.login'))

# Middleware para verificar autenticación (opcional)
def login_required(view):
    from functools import wraps
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor, inicie sesión para acceder a esta página', 'error')
            return redirect(url_for('login.login'))
        return view(*args, **kwargs)
    return wrapped_view

# Middleware para verificar rol de administrador
def admin_required(view):
    from functools import wraps
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor, inicie sesión para acceder a esta página', 'error')
            return redirect(url_for('login.login'))
        if session.get('rol') != 'admin':
            flash('No tienes permisos para acceder a esta página', 'error')
            return redirect(url_for('index'))
        return view(*args, **kwargs)
    return wrapped_view

# Middleware para verificar rol de instructor o admin
def instructor_required(view):
    from functools import wraps
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor, inicie sesión para acceder a esta página', 'error')
            return redirect(url_for('login.login'))
        if session.get('rol') not in ['instructor', 'admin']:
            flash('No tienes permisos para acceder a esta página', 'error')
            return redirect(url_for('index'))
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
        'SELECT * FROM usuarios WHERE email = ? AND activo = 1', (email,)
    ).fetchone()
    conn.close()
    
    if usuario and check_password_hash(usuario['password'], password):
        return jsonify({
            'success': True, 
            'message': 'Login exitoso',
            'user': {
                'id': usuario['id'],
                'nombre': usuario['nombre'],
                'email': usuario['email'],
                'rol': usuario['rol']
            }
        })
    else:
        return jsonify({'success': False, 'message': 'Credenciales incorrectas'}), 401