from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for, session
import sqlite3
import os
from utils.db import get_db_connection
from werkzeug.utils import secure_filename
from routes.login import login_required
from datetime import datetime, timedelta

# Configuración del Blueprint
admin_bp = Blueprint('admin', __name__, template_folder='templates')

# Configuración de subida de imagenes
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def ensure_upload_folder():
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

def is_admin():
    return session.get('user_email') == 'Eduard@gmail.com' or session.get('rol') == 'admin'

def crear_notificacion(tipo, titulo, mensaje, fk_usuario=None, fk_prestamo=None):
    """Crea una notificación en el sistema"""
    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT INTO notificaciones (tipo, titulo, mensaje, fk_usuario, fk_prestamo)
            VALUES (?, ?, ?, ?, ?)
        ''', (tipo, titulo, mensaje, fk_usuario, fk_prestamo))
        conn.commit()
    except Exception as e:
        print(f"Error al crear notificación: {e}")
    finally:
        conn.close()

# Rutas del Blueprint
@admin_bp.route('/admin')
@admin_bp.route('/admin/')
@login_required
def admin():
    if not is_admin():
        flash('No tienes permisos para acceder a esta página', 'error')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    
    # Obtener estadísticas
    total_implementos = conn.execute('SELECT COUNT(*) as count FROM implementos').fetchone()['count']
    total_usuarios = conn.execute('SELECT COUNT(*) as count FROM usuarios').fetchone()['count']
    total_prestamos = conn.execute('SELECT COUNT(*) as count FROM prestamos').fetchone()['count']
    prestamos_activos = conn.execute('SELECT COUNT(*) as count FROM prestamos WHERE fecha_devolucion IS NULL').fetchone()['count']
    
    # Obtener implementos recientes
    implementos = conn.execute('SELECT * FROM implementos ORDER BY fecha_creacion DESC LIMIT 5').fetchall()
    
    # Obtener notificaciones no leídas
    notificaciones = conn.execute('''
        SELECT n.*, u.nombre as usuario_nombre
        FROM notificaciones n
        LEFT JOIN usuarios u ON n.fk_usuario = u.id
        WHERE n.leida = 0
        ORDER BY n.fecha_creacion DESC
        LIMIT 10
    ''').fetchall()
    
    conn.close()
    
    return render_template('admin/panel_administrador.html',
                    total_implementos=total_implementos,
                    total_usuarios=total_usuarios,
                    total_prestamos=total_prestamos,
                    prestamos_activos=prestamos_activos,
                    implementos=implementos,
                    notificaciones=notificaciones)

@admin_bp.route('/admin/catalogo')
@login_required
def ver_catalogo():
    if not is_admin():
        flash('No tienes permisos para acceder a esta página', 'error')
        return redirect(url_for('index'))
    conn = get_db_connection()
    implementos = conn.execute('SELECT * FROM implementos ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('admin/panel_administrador.html', implementos=implementos)

@admin_bp.route('/admin/catalogo/agregar', methods=['GET', 'POST'])
@login_required
def agregar_implemento():
    if not is_admin():
        flash('No tienes permisos para acceder a esta página', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        implemento = request.form.get('implemento')
        descripcion = request.form.get('descripcion')
        disponibilidad = request.form.get('disponibilidad')
        categoria = request.form.get('categoria')
        
        if not all([implemento, descripcion, disponibilidad, categoria]):
            flash('Todos los campos son obligatorios', 'error')
            return render_template('admin/agregar_implemento.html')
        
        imagen_url = None
        if 'imagen' in request.files:
            file = request.files['imagen']
            if file and file.filename != '' and allowed_file(file.filename):
                ensure_upload_folder()
                filename = secure_filename(file.filename)
                unique_filename = f"{os.urandom(8).hex()}_{filename}"
                file.save(os.path.join(UPLOAD_FOLDER, unique_filename))
                imagen_url = unique_filename
        
        conn = get_db_connection()
        try:
            conn.execute(
                'INSERT INTO implementos (implemento, descripcion, disponibilidad, categoria, imagen_url) VALUES (?, ?, ?, ?, ?)',
                (implemento, descripcion, disponibilidad, categoria, imagen_url)
            )
            conn.commit()
            
            # Crear notificación
            crear_notificacion(
                'implemento_nuevo',
                'Nuevo implemento agregado',
                f'{implemento} ha sido agregado al sistema por {session.get("user_nombre")}',
                session.get('user_id')
            )
            
            flash('Implemento agregado correctamente', 'success')
        except sqlite3.Error as e:
            flash(f'Error al guardar en la base de datos: {str(e)}', 'error')
        finally:
            conn.close()
        
        return redirect(url_for('admin.ver_catalogo'))
    
    return render_template('admin/agregar_implemento.html')

@admin_bp.route('/admin/catalogo/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_implemento(id):
    if not is_admin():
        flash('No tienes permisos para acceder a esta página', 'error')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    
    if request.method == 'POST':
        implemento = request.form.get('implemento')
        descripcion = request.form.get('descripcion')
        disponibilidad = request.form.get('disponibilidad')
        categoria = request.form.get('categoria')
        estado = request.form.get('estado', 'Bueno')
        
        if not all([implemento, descripcion, disponibilidad, categoria]):
            flash('Todos los campos son obligatorios', 'error')
            return redirect(url_for('admin.editar_implemento', id=id))
        
        imagen_url = None
        if 'imagen' in request.files:
            file = request.files['imagen']
            if file and file.filename != '' and allowed_file(file.filename):
                ensure_upload_folder()
                filename = secure_filename(file.filename)
                unique_filename = f"{os.urandom(8).hex()}_{filename}"
                file.save(os.path.join(UPLOAD_FOLDER, unique_filename))
                imagen_url = unique_filename
        
        try:
            if imagen_url:
                conn.execute(
                    'UPDATE implementos SET implemento = ?, descripcion = ?, disponibilidad = ?, categoria = ?, imagen_url = ?, estado = ?, fecha_actualizacion = CURRENT_TIMESTAMP WHERE id = ?',
                    (implemento, descripcion, disponibilidad, categoria, imagen_url, estado, id)
                )
            else:
                conn.execute(
                    'UPDATE implementos SET implemento = ?, descripcion = ?, disponibilidad = ?, categoria = ?, estado = ?, fecha_actualizacion = CURRENT_TIMESTAMP WHERE id = ?',
                    (implemento, descripcion, disponibilidad, categoria, estado, id)
                )
            conn.commit()
            flash('Implemento actualizado correctamente', 'success')
        except sqlite3.Error as e:
            flash(f'Error al actualizar: {str(e)}', 'error')
        
        conn.close()
        return redirect(url_for('admin.ver_catalogo'))
    
    implemento = conn.execute('SELECT * FROM implementos WHERE id = ?', (id,)).fetchone()
    conn.close()
    
    if implemento is None:
        flash('Implemento no encontrado', 'error')
        return redirect(url_for('admin.ver_catalogo'))
    
    return render_template('admin/editar_implemento.html', implemento=implemento)

@admin_bp.route('/admin/catalogo/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_implemento(id):
    if not is_admin():
        flash('No tienes permisos para acceder a esta página', 'error')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    
    try:
        implemento = conn.execute('SELECT imagen_url FROM implementos WHERE id = ?', (id,)).fetchone()
        
        if implemento and implemento['imagen_url']:
            try:
                os.remove(os.path.join(UPLOAD_FOLDER, implemento['imagen_url']))
            except OSError:
                pass
        
        conn.execute('DELETE FROM implementos WHERE id = ?', (id,))
        conn.commit()
        flash('Implemento eliminado correctamente', 'success')
    except sqlite3.Error as e:
        flash(f'Error al eliminar: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('admin.ver_catalogo'))

# Gestión de usuarios
@admin_bp.route('/admin/usuarios')
@login_required
def gestion_usuarios():
    if not is_admin():
        flash('No tienes permisos para acceder a esta página', 'error')
        return redirect(url_for('index'))
    conn = get_db_connection()
    usuarios = conn.execute('SELECT * FROM usuarios ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('admin/gestion_usuarios.html', usuarios=usuarios)

# Gestión de préstamos - Devoluciones
@admin_bp.route('/devolucion_prestamos')
@login_required
def devolucion_prestamos():
    if not is_admin():
        flash('No tienes permisos para acceder a esta página', 'error')
        return redirect(url_for('index'))

    conn = get_db_connection()
    
    try:
        prestamos_activos = conn.execute('''
            SELECT p.*, u.nombre as usuario_nombre, i.implemento,
                   julianday('now') - julianday(p.fecha_prestamo) as dias_transcurridos
            FROM prestamos p
            JOIN usuarios u ON p.fk_usuario = u.id
            JOIN implementos i ON p.fk_implemento = i.id
            WHERE p.fecha_devolucion IS NULL
            ORDER BY p.fecha_prestamo DESC
        ''').fetchall()
        
        prestamos_con_dias = []
        for prestamo in prestamos_activos:
            prestamo_dict = dict(prestamo)
            prestamo_dict['dias_transcurridos'] = int(prestamo['dias_transcurridos']) if prestamo['dias_transcurridos'] else 0
            prestamos_con_dias.append(prestamo_dict)
        
        total_prestamos = len(prestamos_con_dias)
        implementos_unicos = len(set(p['fk_implemento'] for p in prestamos_con_dias))
        
        hoy = datetime.now().strftime("%Y-%m-%d")
        prestamos_hoy = conn.execute('''
            SELECT COUNT(*) as count FROM prestamos 
            WHERE DATE(fecha_prestamo) = ? AND fecha_devolucion IS NULL
        ''', (hoy,)).fetchone()['count']
        
    except Exception as e:
        flash(f'Error al cargar préstamos: {str(e)}', 'error')
        prestamos_con_dias = []
        total_prestamos = 0
        implementos_unicos = 0
        prestamos_hoy = 0
    finally:
        conn.close()
    
    return render_template('admin/dvprestamos.html',
                         prestamos_activos=prestamos_con_dias,
                         total_prestamos=total_prestamos,
                         total_implementos=implementos_unicos,
                         prestamos_hoy=prestamos_hoy)

# Procesar devolución desde el panel admin
@admin_bp.route('/devolver_prestamo_admin/<int:id>', methods=['POST'])
@login_required
def devolver_prestamo_admin(id):
    if not is_admin():
        flash('No tienes permisos para acceder a esta página', 'error')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    try:
        # Obtener datos del formulario
        novedad = request.form.get('novedad', 'Ninguna')
        estado_implemento = request.form.get('estado_implemento', 'Bueno')
        observaciones = request.form.get('observaciones', '')
        
        prestamo = conn.execute('''
            SELECT p.*, i.implemento, i.disponibilidad, u.nombre as usuario_nombre
            FROM prestamos p
            JOIN implementos i ON p.fk_implemento = i.id
            JOIN usuarios u ON p.fk_usuario = u.id
            WHERE p.id = ?
        ''', (id,)).fetchone()
        
        if not prestamo:
            flash('No se encontró el préstamo.', 'error')
            return redirect(url_for('admin.devolucion_prestamos'))
        
        if prestamo['fecha_devolucion'] is not None:
            flash('Este préstamo ya fue devuelto anteriormente.', 'warning')
            return redirect(url_for('admin.devolucion_prestamos'))
        
        # Registrar la devolución
        fecha_devolucion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute('''
            UPDATE prestamos 
            SET fecha_devolucion = ?, novedad = ?, estado_implemento_devolucion = ?, observaciones = ?
            WHERE id = ?
        ''', (fecha_devolucion, novedad, estado_implemento, observaciones, id))
        
        # Actualizar disponibilidad del implemento
        nueva_disponibilidad = prestamo['disponibilidad'] + 1
        conn.execute(
            'UPDATE implementos SET disponibilidad = ? WHERE id = ?',
            (nueva_disponibilidad, prestamo['fk_implemento'])
        )
        
        # Actualizar estado del implemento si es necesario
        if estado_implemento != 'Bueno':
            conn.execute(
                'UPDATE implementos SET estado = ? WHERE id = ?',
                (estado_implemento, prestamo['fk_implemento'])
            )
        
        conn.commit()
        
        # Crear notificación
        mensaje_notif = f'Devolución de {prestamo["implemento"]} por {prestamo["usuario_nombre"]}'
        if novedad != 'Ninguna':
            mensaje_notif += f' - Novedad: {novedad}'
        
        crear_notificacion(
            'devolucion',
            'Devolución registrada',
            mensaje_notif,
            session.get('user_id'),
            id
        )
        
        flash(f'Devolución registrada exitosamente: {prestamo["implemento"]}', 'success')
        
    except Exception as e:
        flash(f'Error al procesar la devolución: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('admin.devolucion_prestamos'))

# API para notificaciones
@admin_bp.route('/api/notificaciones')
@login_required
def api_notificaciones():
    if not is_admin():
        return jsonify({'error': 'Sin permisos'}), 403
    
    conn = get_db_connection()
    notificaciones = conn.execute('''
        SELECT n.*, u.nombre as usuario_nombre
        FROM notificaciones n
        LEFT JOIN usuarios u ON n.fk_usuario = u.id
        WHERE n.leida = 0
        ORDER BY n.fecha_creacion DESC
        LIMIT 20
    ''').fetchall()
    conn.close()
    
    return jsonify([dict(notif) for notif in notificaciones])

# Marcar notificación como leída
@admin_bp.route('/api/notificaciones/<int:id>/leer', methods=['POST'])
@login_required
def marcar_notificacion_leida(id):
    if not is_admin():
        return jsonify({'error': 'Sin permisos'}), 403
    
    conn = get_db_connection()
    try:
        conn.execute('UPDATE notificaciones SET leida = 1 WHERE id = ?', (id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# Marcar todas las notificaciones como leídas
@admin_bp.route('/api/notificaciones/leer_todas', methods=['POST'])
@login_required
def marcar_todas_leidas():
    if not is_admin():
        return jsonify({'error': 'Sin permisos'}), 403
    
    conn = get_db_connection()
    try:
        conn.execute('UPDATE notificaciones SET leida = 1 WHERE leida = 0')
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# API estadísticas
@admin_bp.route('/api/admin/estadisticas')
def api_estadisticas():
    conn = get_db_connection()
    
    total_implementos = conn.execute('SELECT COUNT(*) as count FROM implementos').fetchone()['count']
    total_usuarios = conn.execute('SELECT COUNT(*) as count FROM usuarios').fetchone()['count']
    total_prestamos = conn.execute('SELECT COUNT(*) as count FROM prestamos').fetchone()['count']
    prestamos_activos = conn.execute('SELECT COUNT(*) as count FROM prestamos WHERE fecha_devolucion IS NULL').fetchone()['count']
    
    conn.close()
    
    return jsonify({
        'total_implementos': total_implementos,
        'total_usuarios': total_usuarios,
        'total_prestamos': total_prestamos,
        'prestamos_activos': prestamos_activos
    })