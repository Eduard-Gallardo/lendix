from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from routes.login import login_required
from utils.db import get_db_connection
from datetime import datetime

instructor_bp = Blueprint('instructor', __name__, template_folder='templates')

def is_instructor_or_admin():
    """Verificar si el usuario es instructor o admin"""
    return session.get('rol') in ['instructor', 'admin']

# Panel principal del instructor
@instructor_bp.route('/instructor')
@instructor_bp.route('/instructor/')
@login_required
def panel_instructor():
    if not is_instructor_or_admin():
        flash('No tienes permisos para acceder a esta página', 'error')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    
    # Obtener estadísticas
    prestamos_pendientes = conn.execute('''
        SELECT COUNT(*) as count FROM prestamos WHERE estado = 'pendiente'
    ''').fetchone()['count']
    
    reservas_pendientes = conn.execute('''
        SELECT COUNT(*) as count FROM reservas WHERE estado = 'pendiente'
    ''').fetchone()['count']
    
    prestamos_activos = conn.execute('''
        SELECT COUNT(*) as count FROM prestamos WHERE estado = 'activo' AND fecha_devolucion IS NULL
    ''').fetchone()['count']
    
    notificaciones_no_leidas = conn.execute('''
        SELECT COUNT(*) as count FROM notificaciones 
        WHERE fk_instructor = ? AND leida = 0
    ''', (session.get('user_id'),)).fetchone()['count']
    
    # Obtener préstamos pendientes con información detallada
    prestamos_pendientes_list = conn.execute('''
        SELECT p.*, u.nombre as usuario_nombre, c.implemento, c.categoria,
               p.nombre as prestatario_nombre
        FROM prestamos p
        JOIN usuarios u ON p.fk_usuario = u.id
        JOIN catalogo c ON p.fk_modelo = c.id
        WHERE p.estado = 'pendiente'
        ORDER BY p.fecha_prestamo DESC
    ''').fetchall()
    
    # Obtener reservas pendientes
    reservas_pendientes_list = conn.execute('''
        SELECT r.*, u.nombre as usuario_nombre, c.implemento, c.categoria,
               r.nombre as solicitante_nombre
        FROM reservas r
        JOIN usuarios u ON r.fk_usuario = u.id
        JOIN catalogo c ON r.fk_implemento = c.id
        WHERE r.estado = 'pendiente'
        ORDER BY r.fecha_reserva DESC
    ''').fetchall()
    
    # Obtener notificaciones recientes
    notificaciones = conn.execute('''
        SELECT n.*, p.nombre as prestamo_nombre, r.nombre as reserva_nombre,
               c.implemento
        FROM notificaciones n
        LEFT JOIN prestamos p ON n.tipo = 'prestamo' AND n.fk_referencia = p.id
        LEFT JOIN reservas r ON n.tipo = 'reserva' AND n.fk_referencia = r.id
        LEFT JOIN catalogo c ON (p.fk_modelo = c.id OR r.fk_implemento = c.id)
        WHERE n.fk_instructor = ?
        ORDER BY n.created_at DESC
        LIMIT 10
    ''', (session.get('user_id'),)).fetchall()
    
    conn.close()
    
    return render_template('admin/panel_instructor.html',
                         prestamos_pendientes=prestamos_pendientes,
                         reservas_pendientes=reservas_pendientes,
                         prestamos_activos=prestamos_activos,
                         notificaciones_no_leidas=notificaciones_no_leidas,
                         prestamos_pendientes_list=prestamos_pendientes_list,
                         reservas_pendientes_list=reservas_pendientes_list,
                         notificaciones=notificaciones)

# Aprobar préstamo
@instructor_bp.route('/aprobar_prestamo/<int:id>', methods=['POST'])
@login_required
def aprobar_prestamo(id):
    if not is_instructor_or_admin():
        flash('No tienes permisos para aprobar préstamos', 'error')
        return redirect(url_for('instructor.panel_instructor'))
    
    conn = get_db_connection()
    try:
        # Obtener información del préstamo
        prestamo = conn.execute('''
            SELECT p.*, c.implemento, c.disponibilidad 
            FROM prestamos p
            JOIN catalogo c ON p.fk_modelo = c.id
            WHERE p.id = ? AND p.estado = 'pendiente'
        ''', (id,)).fetchone()
        
        if not prestamo:
            flash('No se encontró el préstamo o ya fue procesado.', 'error')
            return redirect(url_for('instructor.panel_instructor'))
        
        # Verificar disponibilidad
        if prestamo['disponibilidad'] <= 0:
            flash('El implemento no tiene disponibilidad para el préstamo.', 'error')
            return redirect(url_for('instructor.panel_instructor'))
        
        # Aprobar préstamo
        conn.execute('''
            UPDATE prestamos 
            SET estado = 'activo', instructor_autorizador = ?
            WHERE id = ?
        ''', (session.get('user_id'), id))
        
        # Actualizar disponibilidad
        nueva_disponibilidad = prestamo['disponibilidad'] - 1
        conn.execute('''
            UPDATE catalogo SET disponibilidad = ? WHERE id = ?
        ''', (nueva_disponibilidad, prestamo['fk_modelo']))
        
        # Marcar notificaciones relacionadas como leídas
        conn.execute('''
            UPDATE notificaciones 
            SET leida = 1 
            WHERE fk_instructor = ? AND tipo = 'prestamo' AND fk_referencia = ?
        ''', (session.get('user_id'), id))
        
        conn.commit()
        flash(f'Préstamo de "{prestamo["implemento"]}" aprobado exitosamente.', 'success')
        
    except Exception as e:
        flash(f'Error al aprobar préstamo: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('instructor.panel_instructor'))

# Rechazar préstamo
@instructor_bp.route('/rechazar_prestamo/<int:id>', methods=['POST'])
@login_required
def rechazar_prestamo(id):
    if not is_instructor_or_admin():
        flash('No tienes permisos para rechazar préstamos', 'error')
        return redirect(url_for('instructor.panel_instructor'))
    
    motivo = request.form.get('motivo', 'No especificado')
    
    conn = get_db_connection()
    try:
        # Obtener información del préstamo
        prestamo = conn.execute('''
            SELECT p.*, c.implemento 
            FROM prestamos p
            JOIN catalogo c ON p.fk_modelo = c.id
            WHERE p.id = ? AND p.estado = 'pendiente'
        ''', (id,)).fetchone()
        
        if not prestamo:
            flash('No se encontró el préstamo o ya fue procesado.', 'error')
            return redirect(url_for('instructor.panel_instructor'))
        
        # Rechazar préstamo
        conn.execute('''
            UPDATE prestamos 
            SET estado = 'rechazado', instructor_autorizador = ?, motivo_rechazo = ?
            WHERE id = ?
        ''', (session.get('user_id'), motivo, id))
        
        # Marcar notificaciones como leídas
        conn.execute('''
            UPDATE notificaciones 
            SET leida = 1 
            WHERE fk_instructor = ? AND tipo = 'prestamo' AND fk_referencia = ?
        ''', (session.get('user_id'), id))
        
        conn.commit()
        flash(f'Préstamo de "{prestamo["implemento"]}" rechazado.', 'info')
        
    except Exception as e:
        flash(f'Error al rechazar préstamo: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('instructor.panel_instructor'))

# Aprobar reserva
@instructor_bp.route('/aprobar_reserva/<int:id>', methods=['POST'])
@login_required
def aprobar_reserva(id):
    if not is_instructor_or_admin():
        flash('No tienes permisos para aprobar reservas', 'error')
        return redirect(url_for('instructor.panel_instructor'))
    
    conn = get_db_connection()
    try:
        # Obtener información de la reserva
        reserva = conn.execute('''
            SELECT r.*, c.implemento, c.disponibilidad 
            FROM reservas r
            JOIN catalogo c ON r.fk_implemento = c.id
            WHERE r.id = ? AND r.estado = 'pendiente'
        ''', (id,)).fetchone()
        
        if not reserva:
            flash('No se encontró la reserva o ya fue procesada.', 'error')
            return redirect(url_for('instructor.panel_instructor'))
        
        # Verificar disponibilidad
        if reserva['disponibilidad'] <= 0:
            flash('El implemento no tiene disponibilidad para la reserva.', 'error')
            return redirect(url_for('instructor.panel_instructor'))
        
        # Verificar conflictos de fechas
        conflictos = conn.execute('''
            SELECT COUNT(*) as count FROM reservas 
            WHERE fk_implemento = ? 
            AND estado = 'aprobada'
            AND (
                (fecha_inicio BETWEEN ? AND ?) OR
                (fecha_fin BETWEEN ? AND ?) OR
                (? BETWEEN fecha_inicio AND fecha_fin) OR
                (? BETWEEN fecha_inicio AND fecha_fin)
            )
            AND id != ?
        ''', (reserva['fk_implemento'], 
              reserva['fecha_inicio'], reserva['fecha_fin'],
              reserva['fecha_inicio'], reserva['fecha_fin'],
              reserva['fecha_inicio'], reserva['fecha_fin'],
              id)).fetchone()['count']
        
        if conflictos > 0:
            flash('Existe un conflicto de horario con otra reserva aprobada.', 'error')
            return redirect(url_for('instructor.panel_instructor'))
        
        # Aprobar reserva
        conn.execute('''
            UPDATE reservas 
            SET estado = 'aprobada', instructor_autorizador = ?
            WHERE id = ?
        ''', (session.get('user_id'), id))
        
        # Actualizar disponibilidad
        nueva_disponibilidad = reserva['disponibilidad'] - 1
        conn.execute('''
            UPDATE catalogo SET disponibilidad = ? WHERE id = ?
        ''', (nueva_disponibilidad, reserva['fk_implemento']))
        
        # Marcar notificaciones como leídas
        conn.execute('''
            UPDATE notificaciones 
            SET leida = 1 
            WHERE fk_instructor = ? AND tipo = 'reserva' AND fk_referencia = ?
        ''', (session.get('user_id'), id))
        
        conn.commit()
        flash(f'Reserva de "{reserva["implemento"]}" aprobada exitosamente.', 'success')
        
    except Exception as e:
        flash(f'Error al aprobar reserva: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('instructor.panel_instructor'))

# Rechazar reserva
@instructor_bp.route('/rechazar_reserva/<int:id>', methods=['POST'])
@login_required
def rechazar_reserva(id):
    if not is_instructor_or_admin():
        flash('No tienes permisos para rechazar reservas', 'error')
        return redirect(url_for('instructor.panel_instructor'))
    
    motivo = request.form.get('motivo', 'No especificado')
    
    conn = get_db_connection()
    try:
        # Obtener información de la reserva
        reserva = conn.execute('''
            SELECT r.*, c.implemento 
            FROM reservas r
            JOIN catalogo c ON r.fk_implemento = c.id
            WHERE r.id = ? AND r.estado = 'pendiente'
        ''', (id,)).fetchone()
        
        if not reserva:
            flash('No se encontró la reserva o ya fue procesada.', 'error')
            return redirect(url_for('instructor.panel_instructor'))
        
        # Rechazar reserva
        conn.execute('''
            UPDATE reservas 
            SET estado = 'rechazada', instructor_autorizador = ?, motivo_rechazo = ?
            WHERE id = ?
        ''', (session.get('user_id'), motivo, id))
        
        # Marcar notificaciones como leídas
        conn.execute('''
            UPDATE notificaciones 
            SET leida = 1 
            WHERE fk_instructor = ? AND tipo = 'reserva' AND fk_referencia = ?
        ''', (session.get('user_id'), id))
        
        conn.commit()
        flash(f'Reserva de "{reserva["implemento"]}" rechazada.', 'info')
        
    except Exception as e:
        flash(f'Error al rechazar reserva: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('instructor.panel_instructor'))

# Marcar todas las notificaciones como leídas
@instructor_bp.route('/marcar_notificaciones_leidas', methods=['POST'])
@login_required
def marcar_notificaciones_leidas():
    if not is_instructor_or_admin():
        flash('No tienes permisos para esta acción', 'error')
        return redirect(url_for('instructor.panel_instructor'))
    
    conn = get_db_connection()
    try:
        conn.execute('''
            UPDATE notificaciones SET leida = 1 
            WHERE fk_instructor = ?
        ''', (session.get('user_id'),))
        conn.commit()
        flash('Todas las notificaciones han sido marcadas como leídas.', 'success')
    except Exception as e:
        flash(f'Error al marcar notificaciones: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('instructor.panel_instructor'))

# Vista de historial de autorizaciones
@instructor_bp.route('/historial_autorizaciones')
@login_required
def historial_autorizaciones():
    if not is_instructor_or_admin():
        flash('No tienes permisos para acceder a esta página', 'error')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    
    # Obtener préstamos autorizados por este instructor
    prestamos_autorizados = conn.execute('''
        SELECT p.*, u.nombre as usuario_nombre, c.implemento, c.categoria,
               p.nombre as prestatario_nombre
        FROM prestamos p
        JOIN usuarios u ON p.fk_usuario = u.id
        JOIN catalogo c ON p.fk_modelo = c.id
        WHERE p.instructor_autorizador = ?
        ORDER BY p.fecha_prestamo DESC
        LIMIT 50
    ''', (session.get('user_id'),)).fetchall()
    
    # Obtener reservas autorizadas por este instructor
    reservas_autorizadas = conn.execute('''
        SELECT r.*, u.nombre as usuario_nombre, c.implemento, c.categoria,
               r.nombre as solicitante_nombre
        FROM reservas r
        JOIN usuarios u ON r.fk_usuario = u.id
        JOIN catalogo c ON r.fk_implemento = c.id
        WHERE r.instructor_autorizador = ?
        ORDER BY r.fecha_reserva DESC
        LIMIT 50
    ''', (session.get('user_id'),)).fetchall()
    
    conn.close()
    
    return render_template('admin/historial_autorizaciones.html',
                         prestamos_autorizados=prestamos_autorizados,
                         reservas_autorizadas=reservas_autorizadas)