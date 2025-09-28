from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from routes.login import login_required
from utils.db import get_db_connection
from datetime import datetime, timedelta

catalogo_bp = Blueprint('catalogo', __name__, template_folder='templates')

def get_user_role():
    """Obtener el rol del usuario actual"""
    return session.get('rol', 'aprendiz')

def can_view_instructor_items(user_role):
    """Verificar si el usuario puede ver items exclusivos para instructores"""
    return user_role in ['instructor', 'admin']

def needs_authorization_for_loan(user_role):
    """Verificar si el usuario necesita autorización para préstamos"""
    return user_role == 'aprendiz'

def create_notification(instructor_id, tipo, referencia_id, mensaje):
    """Crear notificación para instructor"""
    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT INTO notificaciones (fk_instructor, tipo, fk_referencia, mensaje)
            VALUES (?, ?, ?, ?)
        ''', (instructor_id, tipo, referencia_id, mensaje))
        conn.commit()
    except Exception as e:
        print(f"Error creando notificación: {e}")
    finally:
        conn.close()

# Vista principal del catálogo
@catalogo_bp.route('/catalogo', methods=['GET', 'POST'])
@login_required
def catalogo():
    if request.method == 'POST':
        # Solo admin puede agregar implementos
        if session.get('rol') != 'admin':
            flash('No tienes permiso para agregar implementos.', 'error')
            return redirect(url_for('catalogo.catalogo'))

        implemento = request.form.get('implemento')
        descripcion = request.form.get('descripcion')
        disponibilidad = request.form.get('disponibilidad')
        categoria = request.form.get('categoria')
        imagen_url = request.form.get('imagen_url')
        requiere_autorizacion = request.form.get('requiere_autorizacion') == 'on'
        solo_instructores = request.form.get('solo_instructores') == 'on'

        # Validar campos obligatorios
        if not all([implemento, descripcion, disponibilidad, categoria]):
            flash('Todos los campos obligatorios deben ser completados.', 'error')
            return redirect(url_for('catalogo.catalogo'))

        try:
            disponibilidad = int(disponibilidad)
            if disponibilidad < 0:
                flash('La disponibilidad no puede ser negativa.', 'error')
                return redirect(url_for('catalogo.catalogo'))
        except ValueError:
            flash('La disponibilidad debe ser un número entero.', 'error')
            return redirect(url_for('catalogo.catalogo'))

        conn = get_db_connection()
        try:
            conn.execute(
                '''INSERT INTO catalogo (implemento, descripcion, disponibilidad, categoria, imagen_url, requiere_autorizacion, solo_instructores)
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (implemento, descripcion, disponibilidad, categoria, imagen_url, requiere_autorizacion, solo_instructores)
            )
            conn.commit()
            flash('Implemento agregado al catálogo exitosamente.', 'success')
        except Exception as e:
            flash(f'Error al agregar implemento: {str(e)}', 'error')
        finally:
            conn.close()

        return redirect(url_for('catalogo.catalogo'))

    # Obtener catálogo filtrado por rol
    user_role = get_user_role()
    conn = get_db_connection()
    
    if can_view_instructor_items(user_role):
        # Instructores y admins ven todos los implementos
        catalogo_items = conn.execute('SELECT * FROM catalogo WHERE habilitado = 1 ORDER BY implemento').fetchall()
    else:
        # Aprendices y externos solo ven implementos no exclusivos
        catalogo_items = conn.execute('''
            SELECT * FROM catalogo 
            WHERE habilitado = 1 AND solo_instructores = 0 
            ORDER BY implemento
        ''').fetchall()
    
    conn.close()
    return render_template('views/catalogo.html', catalogo=catalogo_items)

# Filtrar catálogo
@catalogo_bp.route('/catalogo/filtrar', methods=['GET'])
@login_required
def filtrar_catalogo():
    filtro = request.args.get('filtro', '')
    categoria = request.args.get('categoria', '')
    disponibilidad = request.args.get('disponibilidad', '')

    user_role = get_user_role()
    conn = get_db_connection()
    
    # Base query según el rol
    if can_view_instructor_items(user_role):
        query = "SELECT * FROM catalogo WHERE habilitado = 1"
    else:
        query = "SELECT * FROM catalogo WHERE habilitado = 1 AND solo_instructores = 0"
    
    params = []

    if categoria:
        query += " AND categoria = ?"
        params.append(categoria)

    if disponibilidad == 'disponible':
        query += " AND disponibilidad > 0"
    elif disponibilidad == 'agotado':
        query += " AND disponibilidad = 0"

    if filtro:
        query += " AND (implemento LIKE ? OR descripcion LIKE ?)"
        params.extend([f'%{filtro}%', f'%{filtro}%'])

    query += " ORDER BY implemento"
    catalogo_items = conn.execute(query, params).fetchall()
    conn.close()

    return render_template('views/catalogo.html',
                           catalogo=catalogo_items,
                           filtro=filtro,
                           categoria=categoria,
                           disponibilidad=disponibilidad)

# Registrar préstamo - MEJORADO CON AUTORIZACIÓN
@catalogo_bp.route('/prestar/<int:id>', methods=['POST'])
@login_required
def prestar(id):
    user_role = get_user_role()
    conn = get_db_connection()
    
    try:
        # Verificar que el implemento existe y está disponible
        implemento = conn.execute('''
            SELECT id, implemento, disponibilidad, requiere_autorizacion, solo_instructores 
            FROM catalogo WHERE id = ?
        ''', (id,)).fetchone()

        if not implemento:
            flash('El implemento no existe.', 'error')
            return redirect(url_for('catalogo.catalogo'))

        # Verificar permisos para ver el implemento
        if implemento['solo_instructores'] and not can_view_instructor_items(user_role):
            flash('No tienes permisos para solicitar este implemento.', 'error')
            return redirect(url_for('catalogo.catalogo'))

        if implemento['disponibilidad'] <= 0:
            flash('Este implemento no está disponible para préstamo.', 'error')
            return redirect(url_for('catalogo.catalogo'))

        fk_usuario = session.get('user_id')
        fecha_prestamo = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fecha_devolucion_estimada = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")

        # Obtener datos del formulario
        nombre_prestatario = request.form.get("nombre")
        instructor = request.form.get("instructor")
        jornada = request.form.get("jornada")
        ambiente = request.form.get("ambiente")

        # Validar campos obligatorios
        if not all([nombre_prestatario, instructor, jornada, ambiente]):
            flash('Todos los campos del préstamo son obligatorios.', 'error')
            return redirect(url_for('catalogo.catalogo'))

        # Determinar el estado inicial según el rol y configuración del implemento
        if needs_authorization_for_loan(user_role) and implemento['requiere_autorizacion']:
            estado_inicial = 'pendiente'
            mensaje_flash = f"Solicitud de préstamo de '{implemento['implemento']}' enviada para autorización"
            
            # Buscar instructores para notificar
            instructores = conn.execute('''
                SELECT id, nombre, email FROM usuarios 
                WHERE rol = 'instructor' AND activo = 1
            ''').fetchall()
            
        else:
            # Instructores, externos y elementos que no requieren autorización se aprueban automáticamente
            estado_inicial = 'activo'
            mensaje_flash = f"Préstamo de '{implemento['implemento']}' registrado con éxito"
            instructores = []

        # Registrar el préstamo
        cursor = conn.execute('''
            INSERT INTO prestamos (fk_usuario, fk_modelo, fecha_prestamo, fecha_devolucion_estimada,
                                 estado, nombre, instructor, jornada, ambiente)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (fk_usuario, id, fecha_prestamo, fecha_devolucion_estimada, estado_inicial, 
              nombre_prestatario, instructor, jornada, ambiente))

        prestamo_id = cursor.lastrowid

        # Si se aprobó automáticamente, actualizar disponibilidad
        if estado_inicial == 'activo':
            nueva_disponibilidad = implemento['disponibilidad'] - 1
            conn.execute('UPDATE catalogo SET disponibilidad = ? WHERE id = ?', 
                        (nueva_disponibilidad, id))

        # Crear notificaciones para instructores si requiere autorización
        if estado_inicial == 'pendiente':
            for instructor_user in instructores:
                mensaje_notificacion = f"Nueva solicitud de préstamo de {implemento['implemento']} por {nombre_prestatario}"
                create_notification(instructor_user['id'], 'prestamo', prestamo_id, mensaje_notificacion)

        conn.commit()
        flash(mensaje_flash, "success")
        
    except Exception as e:
        flash(f"Error en el préstamo: {str(e)}", "error")
    finally:
        conn.close()

    return redirect(url_for('catalogo.catalogo'))

# Registrar reserva - MEJORADO CON AUTORIZACIÓN
@catalogo_bp.route('/reservar/<int:id>', methods=['POST'])
@login_required
def reservar(id):
    user_role = get_user_role()
    conn = get_db_connection()
    
    try:
        # Verificar implemento
        implemento = conn.execute('''
            SELECT id, implemento, disponibilidad, requiere_autorizacion, solo_instructores 
            FROM catalogo WHERE id = ?
        ''', (id,)).fetchone()

        if not implemento:
            flash('El implemento no existe.', 'error')
            return redirect(url_for('catalogo.catalogo'))

        # Verificar permisos
        if implemento['solo_instructores'] and not can_view_instructor_items(user_role):
            flash('No tienes permisos para reservar este implemento.', 'error')
            return redirect(url_for('catalogo.catalogo'))

        if implemento['disponibilidad'] <= 0:
            flash('Este implemento no está disponible para reserva.', 'error')
            return redirect(url_for('catalogo.catalogo'))

        fk_usuario = session.get('user_id')
        fecha_reserva = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Obtener datos del formulario
        nombre = request.form.get("nombre")
        lugar = request.form.get("lugar")
        fecha_inicio = request.form.get("hora_inicio")
        fecha_fin = request.form.get("hora_fin")

        # Validar campos obligatorios
        if not all([nombre, lugar, fecha_inicio, fecha_fin]):
            flash('Todos los campos de la reserva son obligatorios.', 'error')
            return redirect(url_for('catalogo.catalogo'))

        # Validar fechas
        if fecha_inicio >= fecha_fin:
            flash('La fecha de inicio debe ser anterior a la fecha de fin.', 'error')
            return redirect(url_for('catalogo.catalogo'))

        # Determinar estado inicial
        if needs_authorization_for_loan(user_role) and implemento['requiere_autorizacion']:
            estado_inicial = 'pendiente'
            mensaje_flash = f"Solicitud de reserva de '{implemento['implemento']}' enviada para autorización"
            
            # Buscar instructores para notificar
            instructores = conn.execute('''
                SELECT id, nombre, email FROM usuarios 
                WHERE rol = 'instructor' AND activo = 1
            ''').fetchall()
        else:
            estado_inicial = 'aprobada'
            mensaje_flash = f"Reserva de '{implemento['implemento']}' registrada con éxito"
            instructores = []

        # Registrar la reserva
        cursor = conn.execute('''
            INSERT INTO reservas (fk_usuario, fk_implemento, fecha_reserva, fecha_inicio, 
                                fecha_fin, nombre, lugar, estado)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (fk_usuario, id, fecha_reserva, fecha_inicio, fecha_fin, nombre, lugar, estado_inicial))

        reserva_id = cursor.lastrowid

        # Si se aprobó automáticamente, actualizar disponibilidad
        if estado_inicial == 'aprobada':
            nueva_disponibilidad = implemento['disponibilidad'] - 1
            conn.execute('UPDATE catalogo SET disponibilidad = ? WHERE id = ?', 
                        (nueva_disponibilidad, id))

        # Crear notificaciones para instructores si requiere autorización
        if estado_inicial == 'pendiente':
            for instructor_user in instructores:
                mensaje_notificacion = f"Nueva solicitud de reserva de {implemento['implemento']} por {nombre}"
                create_notification(instructor_user['id'], 'reserva', reserva_id, mensaje_notificacion)

        conn.commit()
        flash(mensaje_flash, "success")
        
    except Exception as e:
        flash(f"Error en la reserva: {str(e)}", "error")
    finally:
        conn.close()

    return redirect(url_for('catalogo.catalogo'))

# Devolver implemento (admin y instructores)
@catalogo_bp.route('/devolver/<int:id>', methods=['POST'])
@login_required
def devolver(id):
    user_role = get_user_role()
    if user_role not in ['admin', 'instructor']:
        flash('No tienes permiso para procesar devoluciones.', 'error')
        return redirect(url_for('catalogo.catalogo'))

    conn = get_db_connection()
    try:
        # Buscar el préstamo activo más reciente para este implemento
        prestamo = conn.execute(
            '''SELECT * FROM prestamos 
               WHERE fk_modelo = ? AND fecha_devolucion IS NULL 
               ORDER BY fecha_prestamo DESC LIMIT 1''',
            (id,)
        ).fetchone()

        if not prestamo:
            flash('No se encontró un préstamo activo para este implemento.', 'error')
            return redirect(url_for('catalogo.catalogo'))

        # Registrar la devolución
        fecha_devolucion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            'UPDATE prestamos SET fecha_devolucion = ?, estado = "completado" WHERE id = ?',
            (fecha_devolucion, prestamo['id'])
        )

        # Actualizar la disponibilidad del implemento
        implemento = conn.execute(
            'SELECT disponibilidad FROM catalogo WHERE id = ?', (id,)
        ).fetchone()
        
        if implemento:
            nueva_disponibilidad = implemento['disponibilidad'] + 1
            conn.execute(
                'UPDATE catalogo SET disponibilidad = ? WHERE id = ?',
                (nueva_disponibilidad, id)
            )

        conn.commit()
        flash('Devolución registrada exitosamente.', 'success')

    except Exception as e:
        flash(f'Error al procesar la devolución: {str(e)}', 'error')
    finally:
        conn.close()

    return redirect(url_for('catalogo.catalogo'))

# Resto de las funciones (editar, eliminar, etc.) se mantienen igual
@catalogo_bp.route('/editar_implemento/<int:id>', methods=['POST'])
@login_required
def editar_implemento(id):
    if session.get('rol') != 'admin':
        flash('No tienes permiso para editar implementos.', 'error')
        return redirect(url_for('catalogo.catalogo'))

    implemento = request.form.get('implemento')
    descripcion = request.form.get('descripcion')
    disponibilidad = request.form.get('disponibilidad')
    categoria = request.form.get('categoria')
    imagen_url = request.form.get('imagen_url')
    requiere_autorizacion = request.form.get('requiere_autorizacion') == 'on'
    solo_instructores = request.form.get('solo_instructores') == 'on'

    # Validar campos obligatorios
    if not all([implemento, descripcion, disponibilidad, categoria]):
        flash('Todos los campos obligatorios deben ser completados.', 'error')
        return redirect(url_for('catalogo.catalogo'))

    try:
        disponibilidad = int(disponibilidad)
        if disponibilidad < 0:
            flash('La disponibilidad no puede ser negativa.', 'error')
            return redirect(url_for('catalogo.catalogo'))
    except ValueError:
        flash('La disponibilidad debe ser un número entero.', 'error')
        return redirect(url_for('catalogo.catalogo'))

    conn = get_db_connection()
    try:
        conn.execute(
            '''UPDATE catalogo 
               SET implemento = ?, descripcion = ?, disponibilidad = ?, 
                   categoria = ?, imagen_url = ?, requiere_autorizacion = ?, solo_instructores = ?
               WHERE id = ?''',
            (implemento, descripcion, disponibilidad, categoria, imagen_url, 
             requiere_autorizacion, solo_instructores, id)
        )
        conn.commit()
        flash('Implemento actualizado exitosamente.', 'success')
    except Exception as e:
        flash(f'Error al actualizar implemento: {str(e)}', 'error')
    finally:
        conn.close()

    return redirect(url_for('catalogo.catalogo'))

@catalogo_bp.route('/eliminar_implemento/<int:id>', methods=['POST'])
@login_required
def eliminar_implemento(id):
    if session.get('rol') != 'admin':
        flash('No tienes permiso para eliminar implementos.', 'error')
        return redirect(url_for('catalogo.catalogo'))

    conn = get_db_connection()
    try:
        # Verificar si hay préstamos activos
        prestamos_activos = conn.execute(
            'SELECT COUNT(*) as count FROM prestamos WHERE fk_modelo = ? AND fecha_devolucion IS NULL',
            (id,)
        ).fetchone()

        # Verificar si hay reservas activas
        reservas_activas = conn.execute(
            "SELECT COUNT(*) as count FROM reservas WHERE fk_implemento = ? AND estado IN ('aprobada', 'pendiente')",
            (id,)
        ).fetchone()

        if prestamos_activos['count'] > 0 or reservas_activas['count'] > 0:
            flash('No se puede eliminar el implemento porque tiene préstamos o reservas activas.', 'error')
            return redirect(url_for('catalogo.catalogo'))

        conn.execute('DELETE FROM catalogo WHERE id = ?', (id,))
        conn.commit()
        flash('Implemento eliminado exitosamente.', 'success')
        
    except Exception as e:
        flash(f'Error al eliminar implemento: {str(e)}', 'error')
    finally:
        conn.close()

    return redirect(url_for('catalogo.catalogo'))

@catalogo_bp.route('/')
def habilitar():
    return render_template('views/catalogoins.html')