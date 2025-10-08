from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from routes.login import login_required
from utils.db import get_db_connection
from datetime import datetime, timedelta

prestamos_bp = Blueprint('prestamos', __name__, template_folder='templates')

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
        print(f'Error al crear notificación: {e}')
    finally:
        conn.close()

# Obtener detalles de un préstamo (para modal)
@prestamos_bp.route('/detalle_prestamo/<int:id>', methods=['GET'])
@login_required
def detalle_prestamo(id):
    conn = get_db_connection()
    try:
        prestamo = conn.execute('''
            SELECT p.*, u.nombre as usuario, u.email, i.implemento, i.estado as estado_implemento
            FROM prestamos p
            JOIN usuarios u ON p.fk_usuario = u.id
            JOIN implementos i ON p.fk_implemento = i.id
            WHERE p.id = ?
        ''', (id,)).fetchone()
        
        if not prestamo:
            flash('Préstamo no encontrado.', 'error')
            return redirect(url_for('prestamos.prestamos'))
        
        return render_template('views/detalle_prestamo.html', prestamo=prestamo)
    except Exception as e:
        flash(f'Error al obtener detalles: {str(e)}', 'error')
        return redirect(url_for('prestamos.prestamos'))
    finally:
        conn.close()

# Exportar datos
@prestamos_bp.route('/exportar_prestamos', methods=['GET'])
@login_required
def exportar_prestamos():
    if session.get('rol') != 'admin':
        flash('No tienes permiso para exportar datos.', 'error')
        return redirect(url_for('prestamos.prestamos'))

# Vista principal de gestión de préstamos
@prestamos_bp.route('/prestamos', methods=['GET'])
@login_required
def prestamos():
    conn = get_db_connection()
    
    try:
        # Obtener filtros
        filtro_estado = request.args.get('estado', 'todos')
        filtro_dias = int(request.args.get('dias', 30))
        
        # Construir query base
        query = '''
            SELECT p.*, u.nombre as usuario, i.implemento,
                   julianday('now') - julianday(p.fecha_prestamo) as dias_transcurridos
            FROM prestamos p
            JOIN usuarios u ON p.fk_usuario = u.id
            JOIN implementos i ON p.fk_implemento = i.id
            WHERE 1=1
        '''
        params = []
        
        # Aplicar filtros
        if filtro_estado == 'activos':
            query += " AND p.fecha_devolucion IS NULL"
        elif filtro_estado == 'devueltos':
            query += " AND p.fecha_devolucion IS NOT NULL"
        
        # Filtro por días
        if filtro_dias > 0:
            fecha_limite = (datetime.now() - timedelta(days=filtro_dias)).strftime("%Y-%m-%d")
            query += " AND DATE(p.fecha_prestamo) >= ?"
            params.append(fecha_limite)
        
        # Si no es admin, solo ver sus propios préstamos
        if session.get('rol') != 'admin':
            query += " AND p.fk_usuario = ?"
            params.append(session.get('user_id'))
        
        query += " ORDER BY p.fecha_prestamo DESC"
        
        prestamos_list = conn.execute(query, params).fetchall()
        
        # Calcular estadísticas
        stats = {
            'total_prestamos': len(prestamos_list),
            'prestamos_activos': len([p for p in prestamos_list if p['fecha_devolucion'] is None]),
            'prestamos_devueltos': len([p for p in prestamos_list if p['fecha_devolucion'] is not None])
        }
        
        conn.close()
        
        return render_template('views/prestamos.html',
                             prestamos=prestamos_list,
                             stats=stats,
                             filtro_estado=filtro_estado,
                             filtro_dias=filtro_dias)
    
    except Exception as e:
        flash(f'Error al cargar préstamos: {str(e)}', 'error')
        conn.close()
        return redirect(url_for('index'))

# Procesar devolución de préstamo (solo admin)
@prestamos_bp.route('/devolver_prestamo/<int:id>', methods=['POST'])
@login_required
def devolver_prestamo(id):
    if session.get('rol') != 'admin':
        flash('No tienes permiso para procesar devoluciones.', 'error')
        return redirect(url_for('prestamos.prestamos'))

    conn = get_db_connection()
    try:
        # Obtener datos del formulario
        novedad = request.form.get('novedad', 'Ninguna')
        estado_implemento = request.form.get('estado_implemento', 'Bueno')
        observaciones = request.form.get('observaciones', '')
        
        # Obtener información completa del préstamo
        prestamo = conn.execute('''
            SELECT p.*, i.implemento, i.disponibilidad, u.nombre as usuario_nombre
            FROM prestamos p
            JOIN implementos i ON p.fk_implemento = i.id
            JOIN usuarios u ON p.fk_usuario = u.id
            WHERE p.id = ?
        ''', (id,)).fetchone()

        if not prestamo:
            flash('No se encontró el préstamo.', 'error')
            return redirect(url_for('prestamos.prestamos'))

        if prestamo['fecha_devolucion'] is not None:
            flash('Este préstamo ya fue devuelto anteriormente.', 'warning')
            return redirect(url_for('prestamos.prestamos'))

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
        if estado_implemento != 'Bueno':
            mensaje_notif += f' - Estado: {estado_implemento}'
        
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

    return redirect(url_for('prestamos.prestamos'))