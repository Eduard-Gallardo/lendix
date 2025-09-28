from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
import sqlite3
import re
from utils.db import get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash

# Configuración del Blueprint
registro_bp = Blueprint('registro', __name__, template_folder='templates')

# Rutas del Blueprint
@registro_bp.route('/', methods=['GET', 'POST'])
def registro_usuario():
    if request.method == 'POST':
        # Obtener datos del formulario
        nombre = request.form.get('nombre')
        email = request.form.get('email')
        telefono = request.form.get('telefono')
        rol = request.form.get('rol')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm-password')
        
        # Validar campos obligatorios
        if not all([nombre, email, telefono, rol, password, confirm_password]):
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
        
        # Validar que el rol sea válido
        roles_validos = ['aprendiz', 'instructor', 'externo']
        if rol not in roles_validos:
            flash('Por favor, seleccione un rol válido', 'error')
            return render_template('views/registro.html')
        
        # Validación especial para instructores (requieren email institucional)
        if rol == 'instructor':
            dominios_institucionales = ['sena.edu.co', 'instructor.sena.edu.co']
            dominio_email = email.split('@')[1] if '@' in email else ''
            if dominio_email not in dominios_institucionales:
                flash('Los instructores deben usar un correo institucional (@sena.edu.co)', 'error')
                return render_template('views/registro.html')
        
        # Hash de la contraseña
        hashed_password = generate_password_hash(password)
        
        # Guardar en la base de datos
        conn = get_db_connection()
        try:
            conn.execute(
                'INSERT INTO usuarios (nombre, email, telefono, rol, password) VALUES (?, ?, ?, ?, ?)',
                (nombre, email, telefono, rol, hashed_password)
            )
            conn.commit()
            
            # Mensaje de éxito personalizado según el rol
            if rol == 'instructor':
                flash('¡Cuenta de instructor creada exitosamente! Ya puede iniciar sesión y gestionar préstamos.', 'success')
            elif rol == 'aprendiz':
                flash('¡Cuenta de aprendiz creada exitosamente! Recuerde que los préstamos requieren autorización del instructor.', 'success')
            else:
                flash('¡Cuenta creada exitosamente! Ya puede iniciar sesión.', 'success')
                
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
        
        return redirect(url_for('registro.registro_usuario'))
    
    return render_template('views/registro.html')

# API endpoint para verificar disponibilidad de email
@registro_bp.route('/api/verificar-email', methods=['POST'])
def verificar_email():
    data = request.get_json()
    email = data.get('email', '')
    rol = data.get('rol', '')
    
    if not email:
        return jsonify({'disponible': False, 'mensaje': 'Email requerido'})
    
    # Validar formato
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        return jsonify({'disponible': False, 'mensaje': 'Formato de email inválido'})
    
    # Validar dominio para instructores
    if rol == 'instructor':
        dominios_institucionales = ['sena.edu.co', 'instructor.sena.edu.co']
        dominio_email = email.split('@')[1] if '@' in email else ''
        if dominio_email not in dominios_institucionales:
            return jsonify({'disponible': False, 'mensaje': 'Los instructores deben usar email institucional (@sena.edu.co)'})
    
    # Verificar disponibilidad en la base de datos
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
    
    if len(telefono) < 10:
        return jsonify({'disponible': False, 'mensaje': 'El teléfono debe tener al menos 10 dígitos'})
    
    conn = get_db_connection()
    usuario = conn.execute('SELECT id FROM usuarios WHERE telefono = ?', (telefono,)).fetchone()
    conn.close()
    
    if usuario:
        return jsonify({'disponible': False, 'mensaje': 'Este teléfono ya está registrado'})
    else:
        return jsonify({'disponible': True, 'mensaje': 'Teléfono disponible'})

# API endpoint para obtener información sobre roles
@registro_bp.route('/api/info-roles', methods=['GET'])
def info_roles():
    return jsonify({
        'roles': {
            'aprendiz': {
                'nombre': 'Aprendiz SENA',
                'descripcion': 'Estudiante del SENA. Los préstamos requieren autorización del instructor.',
                'permisos': ['Ver catálogo general', 'Solicitar préstamos (con autorización)', 'Hacer reservas (con autorización)']
            },
            'instructor': {
                'nombre': 'Instructor SENA', 
                'descripcion': 'Docente del SENA. Puede autorizar préstamos y acceder a recursos exclusivos.',
                'permisos': ['Ver todo el catálogo', 'Préstamos automáticos', 'Autorizar préstamos de aprendices', 'Acceso a recursos exclusivos'],
                'requisitos': ['Email institucional (@sena.edu.co)']
            },
            'externo': {
                'nombre': 'Usuario Externo',
                'descripcion': 'Visitante o colaborador externo. Acceso limitado sin autorización.',
                'permisos': ['Ver catálogo general', 'Préstamos automáticos (recursos permitidos)', 'Reservas automáticas']
            }
        }
    })