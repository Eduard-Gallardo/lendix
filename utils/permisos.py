"""
Módulo para manejar permisos de ambientes entre instructores y aprendices
"""

from utils.db import get_db_connection
from datetime import datetime

def es_instructor(user_id):
    """Verifica si un usuario es instructor"""
    conn = get_db_connection()
    try:
        usuario = conn.execute(
            'SELECT tipo_usuario FROM usuarios WHERE id = ?', (user_id,)
        ).fetchone()
        return usuario and usuario['tipo_usuario'] == 'instructor'
    finally:
        conn.close()

def es_aprendiz(user_id):
    """Verifica si un usuario es aprendiz"""
    conn = get_db_connection()
    try:
        usuario = conn.execute(
            'SELECT tipo_usuario FROM usuarios WHERE id = ?', (user_id,)
        ).fetchone()
        return usuario and usuario['tipo_usuario'] == 'aprendiz'
    finally:
        conn.close()

def obtener_instructor_del_aprendiz(aprendiz_id, ambiente):
    """Obtiene el instructor asignado a un aprendiz en un ambiente específico"""
    conn = get_db_connection()
    try:
        asignacion = conn.execute('''
            SELECT fk_instructor FROM asignaciones_aprendices 
            WHERE fk_aprendiz = ? AND ambiente = ? AND activo = 1
        ''', (aprendiz_id, ambiente)).fetchone()
        
        return asignacion['fk_instructor'] if asignacion else None
    finally:
        conn.close()

def verificar_permiso_prestamo(usuario_id, ambiente):
    """
    Verifica si un usuario tiene permiso para solicitar préstamos en un ambiente específico
    """
    conn = get_db_connection()
    try:
        # Si es admin, siempre tiene permiso
        usuario = conn.execute(
            'SELECT tipo_usuario, email FROM usuarios WHERE id = ?', (usuario_id,)
        ).fetchone()
        
        if not usuario:
            return False, "Usuario no encontrado"
            
        # Admin siempre tiene permiso
        if usuario['email'] == 'Eduard@gmail.com':
            return True, "Permiso concedido (Admin)"
            
        # Si es instructor, siempre tiene permiso
        if usuario['tipo_usuario'] == 'instructor':
            return True, "Permiso concedido (Instructor)"
            
        # Si es aprendiz, verificar permisos
        if usuario['tipo_usuario'] == 'aprendiz':
            # Obtener instructor asignado
            instructor_id = obtener_instructor_del_aprendiz(usuario_id, ambiente)
            
            if not instructor_id:
                return False, f"No tienes un instructor asignado para el ambiente '{ambiente}'"
            
            # Verificar si el instructor ha habilitado el ambiente
            permiso = conn.execute('''
                SELECT habilitado FROM permisos_ambientes 
                WHERE fk_instructor = ? AND ambiente = ?
            ''', (instructor_id, ambiente)).fetchone()
            
            if not permiso:
                return False, f"El instructor no ha configurado permisos para el ambiente '{ambiente}'"
            
            if permiso['habilitado']:
                return True, "Permiso concedido por instructor"
            else:
                return False, f"El instructor ha deshabilitado los préstamos para el ambiente '{ambiente}'"
        
        return False, "Tipo de usuario no reconocido"
        
    finally:
        conn.close()

def crear_permiso_ambiente(instructor_id, ambiente, habilitado=True):
    """Crea o actualiza un permiso de ambiente para un instructor"""
    conn = get_db_connection()
    try:
        # Verificar si ya existe
        permiso_existente = conn.execute('''
            SELECT id FROM permisos_ambientes 
            WHERE fk_instructor = ? AND ambiente = ?
        ''', (instructor_id, ambiente)).fetchone()
        
        if permiso_existente:
            # Actualizar permiso existente
            conn.execute('''
                UPDATE permisos_ambientes 
                SET habilitado = ?, fecha_modificacion = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (habilitado, permiso_existente['id']))
        else:
            # Crear nuevo permiso
            conn.execute('''
                INSERT INTO permisos_ambientes (fk_instructor, ambiente, habilitado)
                VALUES (?, ?, ?)
            ''', (instructor_id, ambiente, habilitado))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error al crear/actualizar permiso: {e}")
        return False
    finally:
        conn.close()

def asignar_aprendiz_a_instructor(instructor_id, aprendiz_id, ambiente):
    """Asigna un aprendiz a un instructor en un ambiente específico"""
    conn = get_db_connection()
    try:
        # Verificar si ya existe la asignación
        asignacion_existente = conn.execute('''
            SELECT id FROM asignaciones_aprendices 
            WHERE fk_instructor = ? AND fk_aprendiz = ? AND ambiente = ?
        ''', (instructor_id, aprendiz_id, ambiente)).fetchone()
        
        if asignacion_existente:
            # Reactivar asignación existente
            conn.execute('''
                UPDATE asignaciones_aprendices 
                SET activo = 1, fecha_asignacion = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (asignacion_existente['id'],))
        else:
            # Crear nueva asignación
            conn.execute('''
                INSERT INTO asignaciones_aprendices (fk_instructor, fk_aprendiz, ambiente)
                VALUES (?, ?, ?)
            ''', (instructor_id, aprendiz_id, ambiente))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error al asignar aprendiz: {e}")
        return False
    finally:
        conn.close()

def obtener_aprendices_del_instructor(instructor_id, ambiente=None):
    """Obtiene todos los aprendices asignados a un instructor"""
    conn = get_db_connection()
    try:
        if ambiente:
            query = '''
                SELECT u.id, u.nombre, u.email, u.telefono, a.fecha_asignacion
                FROM usuarios u
                JOIN asignaciones_aprendices a ON u.id = a.fk_aprendiz
                WHERE a.fk_instructor = ? AND a.ambiente = ? AND a.activo = 1
                ORDER BY u.nombre
            '''
            params = (instructor_id, ambiente)
        else:
            query = '''
                SELECT u.id, u.nombre, u.email, u.telefono, a.ambiente, a.fecha_asignacion
                FROM usuarios u
                JOIN asignaciones_aprendices a ON u.id = a.fk_aprendiz
                WHERE a.fk_instructor = ? AND a.activo = 1
                ORDER BY a.ambiente, u.nombre
            '''
            params = (instructor_id,)
        
        return conn.execute(query, params).fetchall()
    finally:
        conn.close()

def obtener_permisos_instructor(instructor_id):
    """Obtiene todos los permisos de ambientes de un instructor"""
    conn = get_db_connection()
    try:
        return conn.execute('''
            SELECT ambiente, habilitado, fecha_creacion, fecha_modificacion
            FROM permisos_ambientes
            WHERE fk_instructor = ?
            ORDER BY ambiente
        ''', (instructor_id,)).fetchall()
    finally:
        conn.close()

def obtener_ambientes_disponibles():
    """Obtiene una lista de ambientes disponibles en el sistema"""
    # Lista predefinida de ambientes comunes en el SENA
    return [
        'Aula 101', 'Aula 102', 'Aula 103', 'Aula 104', 'Aula 105',
        'Laboratorio de Sistemas', 'Laboratorio de Redes', 'Laboratorio de Electrónica',
        'Taller de Mecánica', 'Taller de Soldadura', 'Taller de Carpintería',
        'Biblioteca', 'Sala de Estudio', 'Auditorio', 'Sala de Conferencias',
        'Cafetería', 'Patio Central', 'Cancha Deportiva', 'Gimnasio'
    ]
