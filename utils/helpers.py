"""
Utilidades y funciones auxiliares para el sistema Lendix
"""
from utils.db import get_db_connection
from datetime import datetime

def crear_notificacion(tipo, titulo, mensaje, fk_usuario=None, fk_prestamo=None):
    """
    Crea una notificación en el sistema
    
    Args:
        tipo: Tipo de notificación (prestamo_individual, prestamo_multiple, devolucion, implemento_nuevo)
        titulo: Título de la notificación
        mensaje: Mensaje descriptivo
        fk_usuario: ID del usuario relacionado (opcional)
        fk_prestamo: ID del préstamo relacionado (opcional)
    """
    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT INTO notificaciones (tipo, titulo, mensaje, fk_usuario, fk_prestamo)
            VALUES (?, ?, ?, ?, ?)
        ''', (tipo, titulo, mensaje, fk_usuario, fk_prestamo))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error al crear notificación: {e}")
        return False
    finally:
        conn.close()

def obtener_estadisticas_dashboard():
    """
    Obtiene estadísticas generales para el dashboard
    
    Returns:
        dict: Diccionario con estadísticas del sistema
    """
    conn = get_db_connection()
    try:
        stats = {}
        
        # Implementos
        stats['total_implementos'] = conn.execute(
            'SELECT COUNT(*) as count FROM implementos'
        ).fetchone()['count']
        
        stats['implementos_disponibles'] = conn.execute(
            'SELECT COUNT(*) as count FROM implementos WHERE disponibilidad > 0'
        ).fetchone()['count']
        
        # Usuarios
        stats['total_usuarios'] = conn.execute(
            'SELECT COUNT(*) as count FROM usuarios WHERE activo = 1'
        ).fetchone()['count']
        
        # Préstamos
        stats['total_prestamos'] = conn.execute(
            'SELECT COUNT(*) as count FROM prestamos'
        ).fetchone()['count']
        
        stats['prestamos_activos'] = conn.execute(
            'SELECT COUNT(*) as count FROM prestamos WHERE fecha_devolucion IS NULL'
        ).fetchone()['count']
        
        stats['prestamos_hoy'] = conn.execute(
            '''SELECT COUNT(*) as count FROM prestamos 
               WHERE DATE(fecha_prestamo) = DATE('now')'''
        ).fetchone()['count']
        
        # Notificaciones
        stats['notificaciones_pendientes'] = conn.execute(
            'SELECT COUNT(*) as count FROM notificaciones WHERE leida = 0'
        ).fetchone()['count']
        
        return stats
    except Exception as e:
        print(f"Error al obtener estadísticas: {e}")
        return {}
    finally:
        conn.close()

def verificar_disponibilidad_implemento(implemento_id):
    """
    Verifica si un implemento está disponible para préstamo
    
    Args:
        implemento_id: ID del implemento
        
    Returns:
        tuple: (bool disponible, str mensaje)
    """
    conn = get_db_connection()
    try:
        implemento = conn.execute(
            'SELECT disponibilidad, estado FROM implementos WHERE id = ?',
            (implemento_id,)
        ).fetchone()
        
        if not implemento:
            return False, "El implemento no existe"
        
        if implemento['disponibilidad'] <= 0:
            return False, "No hay unidades disponibles"
        
        if implemento['estado'] == 'Dañado':
            return False, "El implemento está dañado y no puede ser prestado"
        
        return True, "Disponible"
    except Exception as e:
        return False, f"Error al verificar disponibilidad: {str(e)}"
    finally:
        conn.close()

def registrar_accion_historial(usuario_id, accion, detalle=None, ip_address=None):
    """
    Registra una acción en el historial de auditoría
    
    Args:
        usuario_id: ID del usuario que realiza la acción
        accion: Descripción de la acción
        detalle: Detalle adicional (opcional)
        ip_address: Dirección IP del usuario (opcional)
    """
    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT INTO historial_acciones (fk_usuario, accion, detalle, ip_address)
            VALUES (?, ?, ?, ?)
        ''', (usuario_id, accion, detalle, ip_address))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error al registrar en historial: {e}")
        return False
    finally:
        conn.close()

def obtener_prestamos_usuario(usuario_id, incluir_devueltos=False):
    """
    Obtiene los préstamos de un usuario específico
    
    Args:
        usuario_id: ID del usuario
        incluir_devueltos: Si se deben incluir préstamos devueltos
        
    Returns:
        list: Lista de préstamos del usuario
    """
    conn = get_db_connection()
    try:
        query = '''
            SELECT p.*, i.implemento, i.categoria
            FROM prestamos p
            JOIN implementos i ON p.fk_implemento = i.id
            WHERE p.fk_usuario = ?
        '''
        
        if not incluir_devueltos:
            query += ' AND p.fecha_devolucion IS NULL'
        
        query += ' ORDER BY p.fecha_prestamo DESC'
        
        prestamos = conn.execute(query, (usuario_id,)).fetchall()
        return [dict(p) for p in prestamos]
    except Exception as e:
        print(f"Error al obtener préstamos: {e}")
        return []
    finally:
        conn.close()

def calcular_dias_prestamo(fecha_prestamo):
    """
    Calcula los días transcurridos desde un préstamo
    
    Args:
        fecha_prestamo: Fecha del préstamo (string)
        
    Returns:
        int: Número de días transcurridos
    """
    try:
        fecha_prestamo_dt = datetime.strptime(fecha_prestamo, "%Y-%m-%d %H:%M:%S")
        dias = (datetime.now() - fecha_prestamo_dt).days
        return dias
    except Exception as e:
        print(f"Error al calcular días: {e}")
        return 0

def validar_rol_usuario(usuario_id, roles_permitidos):
    """
    Valida si un usuario tiene uno de los roles permitidos
    
    Args:
        usuario_id: ID del usuario
        roles_permitidos: Lista de roles permitidos
        
    Returns:
        bool: True si el usuario tiene un rol permitido
    """
    conn = get_db_connection()
    try:
        usuario = conn.execute(
            'SELECT rol FROM usuarios WHERE id = ?',
            (usuario_id,)
        ).fetchone()
        
        if not usuario:
            return False
        
        return usuario['rol'] in roles_permitidos
    except Exception as e:
        print(f"Error al validar rol: {e}")
        return False
    finally:
        conn.close()

def obtener_implementos_con_problemas():
    """
    Obtiene implementos con desgaste o daños
    
    Returns:
        list: Lista de implementos con problemas
    """
    conn = get_db_connection()
    try:
        implementos = conn.execute('''
            SELECT * FROM implementos 
            WHERE estado IN ('Desgaste notable', 'Dañado')
            ORDER BY estado DESC, implemento
        ''').fetchall()
        return [dict(i) for i in implementos]
    except Exception as e:
        print(f"Error al obtener implementos con problemas: {e}")
        return []
    finally:
        conn.close()

def generar_reporte_prestamos(fecha_inicio=None, fecha_fin=None):
    """
    Genera un reporte de préstamos en un rango de fechas
    
    Args:
        fecha_inicio: Fecha de inicio (opcional)
        fecha_fin: Fecha de fin (opcional)
        
    Returns:
        dict: Reporte con estadísticas
    """
    conn = get_db_connection()
    try:
        query = '''
            SELECT 
                COUNT(*) as total_prestamos,
                COUNT(CASE WHEN fecha_devolucion IS NULL THEN 1 END) as activos,
                COUNT(CASE WHEN fecha_devolucion IS NOT NULL THEN 1 END) as devueltos,
                COUNT(CASE WHEN tipo_prestamo = 'individual' THEN 1 END) as individuales,
                COUNT(CASE WHEN tipo_prestamo = 'multiple' THEN 1 END) as multiples
            FROM prestamos
            WHERE 1=1
        '''
        params = []
        
        if fecha_inicio:
            query += ' AND DATE(fecha_prestamo) >= ?'
            params.append(fecha_inicio)
        
        if fecha_fin:
            query += ' AND DATE(fecha_prestamo) <= ?'
            params.append(fecha_fin)
        
        reporte = conn.execute(query, params).fetchone()
        return dict(reporte)
    except Exception as e:
        print(f"Error al generar reporte: {e}")
        return {}
    finally:
        conn.close()