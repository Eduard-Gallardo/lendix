from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
import sqlite3
import re
from utils.db import get_db_connection
from werkzeug.security import generate_password_hash

# Configuración del Blueprint
registro_bp = Blueprint('registro', __name__, template_folder='templates')

@registro_bp.route('/', methods=['GET', 'POST'])
def registro_usuario():
    if request.method == 'POST':
        # Obtener datos del formulario
        nombre = request.form.get('nombre')
        email = request.form.get('email')
        telefono = request.form.get('telefono')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm-password')
        tipo_usuario = request.form.get('tipo_usuario', 'funcionario')
        
        # Validar que el tipo de usuario sea válido (solo instructor o funcionario)
        if tipo_usuario not in ['instructor', 'funcionario']:
            tipo_usuario = 'funcionario'
        
        # Validar campos obligatorios
        if not all([nombre, email, telefono, password, confirm_password]):
            flash('Todos los campos son obligatorios', 'error')
            return render_template('views/registro.html')
        
        # Validar que las contraseñas coincidan
        if password != confirm_password:
            flash('Las contraseñas no coinciden', 'error')
            return render_template('views/registro.html')
        
        # Validar formato de email
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            flash('Por favor, ingrese un correo electrónico válido', 'error')
            return render_template('views/registro.html')
        
        # Validar formato de teléfono (mínimo 10 caracteres)
        if len(telefono) < 10:
            flash('El teléfono debe tener al menos 10 caracteres', 'error')
            return render_template('views/registro.html')
        
        # Validar fortaleza de contraseña
        if len(password) < 8:
            flash('La contraseña debe tener al menos 8 caracteres', 'error')
            return render_template('views/registro.html')
        
        # Hash de la contraseña
        hashed_password = generate_password_hash(password)
        
        # Guardar en la base de datos
        conn = get_db_connection()
        try:
            conn.execute(
                'INSERT INTO usuarios (nombre, email, telefono, password, rol, activo) VALUES (?, ?, ?, ?, ?, ?)',
                (nombre, email, telefono, hashed_password, tipo_usuario, 0)
            )
            conn.commit()
            flash('¡Cuenta creada exitosamente! Un administrador debe aprobar tu acceso antes de poder iniciar sesión.', 'success')
            
            # Registrar en historial
            try:
                from utils.helpers import registrar_accion_historial
                usuario_id = conn.execute('SELECT id FROM usuarios WHERE email = ?', (email,)).fetchone()['id']
                registrar_accion_historial(
                    usuario_id,
                    'Registro de usuario',
                    f'Nuevo usuario registrado: {nombre} ({tipo_usuario})',
                    request.remote_addr
                )
            except:
                pass
                
        except sqlite3.IntegrityError as e:
            if 'UNIQUE constraint failed: usuarios.email' in str(e):
                flash('Este correo electrónico ya está registrado', 'error')
            elif 'UNIQUE constraint failed: usuarios.telefono' in str(e):
                flash('Este número de teléfono ya está registrado', 'error')
            elif 'UNIQUE constraint failed: usuarios.nombre' in str(e):
                flash('Este nombre de usuario ya está registrado', 'error')
            else:
                flash('Error al crear la cuenta. Por favor, intente nuevamente.', 'error')
        except sqlite3.Error as e:
            flash(f'Error al guardar en la base de datos: {str(e)}', 'error')
        finally:
            conn.close()
        
        return redirect(url_for('login.login'))
    
    return render_template('views/registro.html')

# API endpoint para verificar disponibilidad de email
@registro_bp.route('/api/verificar-email', methods=['POST'])
def verificar_email():
    data = request.get_json()
    email = data.get('email', '')
    
    if not email:
        return jsonify({'disponible': False, 'mensaje': 'Email requerido'})
    
    conn = get_db_connection()
    usuario = conn.execute('SELECT id FROM usuarios WHERE email = ?', (email,)).fetchone()
    conn.close()
    
    if usuario:
        return jsonify({'disponible': False, 'mensaje': 'Este email ya está registrado'})
    else:
        return jsonify({'disponible': True, 'mensaje': 'Email disponible'})

# API endpoint para verificar disponibilidad de teléfono
@registro_bp.route('/api/verificar-telefono', methods=['POST'])
def verificar_telefono():
    data = request.get_json()
    telefono = data.get('telefono', '')
    
    if not telefono:
        return jsonify({'disponible': False, 'mensaje': 'Teléfono requerido'})
    
    conn = get_db_connection()
    usuario = conn.execute('SELECT id FROM usuarios WHERE telefono = ?', (telefono,)).fetchone()
    conn.close()
    
    if usuario:
        return jsonify({'disponible': False, 'mensaje': 'Este teléfono ya está registrado'})
    else:
        return jsonify({'disponible': True, 'mensaje': 'Teléfono disponible'})

# API endpoint para verificar nombre de usuario
@registro_bp.route('/api/verificar-nombre', methods=['POST'])
def verificar_nombre():
    data = request.get_json()
    nombre = data.get('nombre', '')
    
    if not nombre:
        return jsonify({'disponible': False, 'mensaje': 'Nombre requerido'})
    
    conn = get_db_connection()
    usuario = conn.execute('SELECT id FROM usuarios WHERE nombre = ?', (nombre,)).fetchone()
    conn.close()
    
    if usuario:
        return jsonify({'disponible': False, 'mensaje': 'Este nombre ya está registrado'})
    else:
        return jsonify({'disponible': True, 'mensaje': 'Nombre disponible'})