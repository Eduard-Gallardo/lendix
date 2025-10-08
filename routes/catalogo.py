from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from routes.login import login_required
from utils.db import get_db_connection
from datetime import datetime

catalogo_bp = Blueprint('catalogo', __name__, template_folder='templates')

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

# Vista principal del catálogo
@catalogo_bp.route('/catalogo', methods=['GET', 'POST'])
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
                '''INSERT INTO implementos (implemento, descripcion, disponibilidad, categoria, imagen_url)
                   VALUES (?, ?, ?, ?, ?)''',
                (implemento, descripcion, disponibilidad, categoria, imagen_url)
            )
            conn.commit()
            
            # Crear notificación para admin
            crear_notificacion(
                'implemento_nuevo',
                'Nuevo implemento agregado',
                f'{implemento} ha sido agregado al catálogo por {session.get("user_nombre")}',
                session.get('user_id')
            )
            
            flash('Implemento agregado al catálogo exitosamente.', 'success')
        except Exception as e:
            flash(f'Error al agregar implemento: {str(e)}', 'error')
        finally:
            conn.close()

        return redirect(url_for('catalogo.catalogo'))

    conn = get_db_connection()
    catalogo_items = conn.execute('SELECT * FROM implementos ORDER BY implemento').fetchall()
    conn.close()
    return render_template('views/catalogo.html', catalogo=catalogo_items)

# Filtrar catálogo
@catalogo_bp.route('/catalogo/filtrar', methods=['GET'])
@login_required
def filtrar_catalogo():
    filtro = request.args.get('filtro', '')
    categoria = request.args.get('categoria', '')
    disponibilidad = request.args.get('disponibilidad', '')

    conn = get_db_connection()
    query = "SELECT * FROM implementos WHERE 1=1"
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

# Registrar préstamo
@catalogo_bp.route('/prestar/<int:id>', methods=['POST'])
@login_required
def prestar(id):
    # Solo instructores y funcionarios pueden hacer préstamos
    if session.get('rol') not in ['instructor', 'funcionario']:
        flash('No tienes permiso para realizar préstamos.', 'error')
        return redirect(url_for('catalogo.catalogo'))
    
    conn = get_db_connection()
    try:
        # Obtener datos del formulario
        tipo_prestamo = request.form.get('tipo_prestamo')
        nombre_prestatario = request.form.get('nombre_prestatario')
        jornada = request.form.get('jornada')
        
        # El instructor es el usuario logueado
        instructor = session.get('user_nombre', 'Usuario')
        
        if not all([tipo_prestamo, nombre_prestatario, jornada]):
            flash('Todos los campos obligatorios deben ser completados.', 'error')
            return redirect(url_for('catalogo.catalogo'))

        # Obtener cantidad solicitada
        try:
            cantidad_solicitada = int(request.form.get('cantidad', 1))
        except (ValueError, TypeError):
            cantidad_solicitada = 1
        
        # Verificar disponibilidad del implemento
        implemento = conn.execute(
            'SELECT id, implemento, disponibilidad FROM implementos WHERE id = ?', (id,)
        ).fetchone()

        if not implemento:
            flash('El implemento no existe.', 'error')
            return redirect(url_for('catalogo.catalogo'))

        if implemento['disponibilidad'] <= 0:
            flash('Este implemento no está disponible para préstamo.', 'error')
            return redirect(url_for('catalogo.catalogo'))
            
        # Validar cantidad solicitada vs disponibilidad
        if cantidad_solicitada > implemento['disponibilidad']:
            flash(f'Solo hay {implemento["disponibilidad"]} unidad{"es" if implemento["disponibilidad"] > 1 else ""} disponible{"s" if implemento["disponibilidad"] > 1 else ""} de {implemento["implemento"]}. Has solicitado {cantidad_solicitada}.', 'error')
            return redirect(url_for('catalogo.catalogo'))
            
        if cantidad_solicitada <= 0:
            flash('La cantidad debe ser mayor a 0.', 'error')
            return redirect(url_for('catalogo.catalogo'))

        fk_usuario = session.get('user_id')
        fecha_prestamo = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Crear registros de préstamo según la cantidad solicitada
        prestamos_ids = []
        
        for i in range(cantidad_solicitada):
            if tipo_prestamo == 'individual':
                ambiente = request.form.get('ambiente') or 'SENA'
                
                # Registrar el préstamo individual
                cursor = conn.execute('''
                    INSERT INTO prestamos (fk_usuario, fk_implemento, tipo_prestamo, nombre_prestatario, 
                                        instructor, jornada, ambiente, fecha_prestamo)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (fk_usuario, id, 'individual', nombre_prestatario, instructor, jornada, ambiente, fecha_prestamo))
                
                if i == 0:  # Solo para el primer préstamo
                    tipo_notificacion = 'prestamo_individual'
                    mensaje_notificacion = f'{nombre_prestatario} ha solicitado {cantidad_solicitada} préstamo{"s" if cantidad_solicitada > 1 else ""} individual{"es" if cantidad_solicitada > 1 else ""} de {implemento["implemento"]}'
                
            else:  # tipo_prestamo == 'multiple'
                ficha = request.form.get('ficha')
                horario = request.form.get('horario')
                ambiente = request.form.get('ambiente')
                
                if not all([ficha, horario, ambiente]):
                    flash('Para préstamo múltiple, ficha, horario y ambiente son obligatorios.', 'error')
                    return redirect(url_for('catalogo.catalogo'))
                
                # Registrar el préstamo múltiple
                cursor = conn.execute('''
                    INSERT INTO prestamos (fk_usuario, fk_implemento, tipo_prestamo, nombre_prestatario, 
                                        instructor, jornada, ficha, horario, ambiente, fecha_prestamo)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (fk_usuario, id, 'multiple', nombre_prestatario, instructor, jornada, ficha, horario, ambiente, fecha_prestamo))
                
                if i == 0:  # Solo para el primer préstamo
                    tipo_notificacion = 'prestamo_multiple'
                    mensaje_notificacion = f'{nombre_prestatario} ha solicitado {cantidad_solicitada} préstamo{"s" if cantidad_solicitada > 1 else ""} múltiple{"s" if cantidad_solicitada > 1 else ""} de {implemento["implemento"]} - Ficha: {ficha}'
            
            prestamos_ids.append(cursor.lastrowid)

        prestamo_id = prestamos_ids[0]  # Usar el primer ID para la notificación

        # Actualizar la disponibilidad del implemento
        nueva_disponibilidad = implemento['disponibilidad'] - cantidad_solicitada
        conn.execute('UPDATE implementos SET disponibilidad = ? WHERE id = ?', 
                    (nueva_disponibilidad, id))

        conn.commit()
        
        # Crear notificación para admin
        crear_notificacion(
            tipo_notificacion,
            f'Nuevo préstamo {tipo_prestamo}',
            mensaje_notificacion,
            fk_usuario,
            prestamo_id
        )
        
        flash(f"{cantidad_solicitada} préstamo{'s' if cantidad_solicitada > 1 else ''} {tipo_prestamo}{'s' if cantidad_solicitada > 1 else ''} de '{implemento['implemento']}' registrado{'s' if cantidad_solicitada > 1 else ''} con éxito", "success")
        
    except Exception as e:
        flash(f"Error en el préstamo: {str(e)}", "error")
    finally:
        conn.close()

    return redirect(url_for('catalogo.catalogo'))

# Registrar préstamo múltiple
@catalogo_bp.route('/prestar_multiple/<int:id>', methods=['POST'])
@login_required
def prestar_multiple(id):
    # Solo instructores y funcionarios pueden hacer préstamos
    if session.get('rol') not in ['instructor', 'funcionario']:
        flash('No tienes permiso para realizar préstamos.', 'error')
        return redirect(url_for('catalogo.catalogo'))
    
    conn = get_db_connection()
    try:
        # Obtener cantidad solicitada
        try:
            cantidad_solicitada = int(request.form.get('cantidad', 1))
        except (ValueError, TypeError):
            cantidad_solicitada = 1
        
        # Verificar disponibilidad del implemento
        implemento = conn.execute(
            'SELECT id, implemento, disponibilidad FROM implementos WHERE id = ?', (id,)
        ).fetchone()

        if not implemento:
            flash('El implemento no existe.', 'error')
            return redirect(url_for('catalogo.catalogo'))

        if implemento['disponibilidad'] <= 0:
            flash('Este implemento no está disponible para préstamo.', 'error')
            return redirect(url_for('catalogo.catalogo'))
            
        # Validar cantidad solicitada vs disponibilidad
        if cantidad_solicitada > implemento['disponibilidad']:
            flash(f'Solo hay {implemento["disponibilidad"]} unidad{"es" if implemento["disponibilidad"] > 1 else ""} disponible{"s" if implemento["disponibilidad"] > 1 else ""} de {implemento["implemento"]}. Has solicitado {cantidad_solicitada}.', 'error')
            return redirect(url_for('catalogo.catalogo'))
            
        if cantidad_solicitada <= 0:
            flash('La cantidad debe ser mayor a 0.', 'error')
            return redirect(url_for('catalogo.catalogo'))

        fk_usuario = session.get('user_id')
        fecha_prestamo = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # El nombre del prestatario es el usuario que hace el préstamo
        nombre_prestatario = session.get('user_nombre')
        
        # Obtener datos adicionales del formulario
        ficha = request.form.get("ficha")
        ambiente = request.form.get("ambiente")
        horario = request.form.get("horario")

        # Validar campos obligatorios para préstamo múltiple
        if not all([ficha, ambiente, horario]):
            flash('Para préstamo múltiple, ficha, ambiente y horario son obligatorios.', 'error')
            return redirect(url_for('catalogo.catalogo'))

        # Crear registros de préstamo según la cantidad solicitada
        prestamos_ids = []
        
        for i in range(cantidad_solicitada):
            # Registrar el préstamo múltiple
            cursor = conn.execute('''
                INSERT INTO prestamos (fk_usuario, fk_implemento, tipo_prestamo, nombre_prestatario, 
                                    ficha, ambiente, horario, fecha_prestamo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (fk_usuario, id, 'multiple', nombre_prestatario, ficha, ambiente, horario, fecha_prestamo))
            
            prestamos_ids.append(cursor.lastrowid)
        
        prestamo_id = prestamos_ids[0]  # Usar el primer ID para la notificación

        # Actualizar la disponibilidad del implemento
        nueva_disponibilidad = implemento['disponibilidad'] - cantidad_solicitada
        conn.execute('UPDATE implementos SET disponibilidad = ? WHERE id = ?', 
                    (nueva_disponibilidad, id))

        conn.commit()
        
        # Crear notificación para admin
        crear_notificacion(
            'prestamo_multiple',
            'Nuevo préstamo múltiple',
            f'{nombre_prestatario} ha solicitado {cantidad_solicitada} préstamo{"s" if cantidad_solicitada > 1 else ""} múltiple{"s" if cantidad_solicitada > 1 else ""} de {implemento["implemento"]} - Ficha: {ficha}, Ambiente: {ambiente}',
            fk_usuario,
            prestamo_id
        )
        
        flash(f"{cantidad_solicitada} préstamo{'s' if cantidad_solicitada > 1 else ''} múltiple{'s' if cantidad_solicitada > 1 else ''} de '{implemento['implemento']}' registrado{'s' if cantidad_solicitada > 1 else ''} con éxito", "success")
        
    except Exception as e:
        flash(f"Error en el préstamo: {str(e)}", "error")
    finally:
        conn.close()

    return redirect(url_for('catalogo.catalogo'))

# Editar implemento (solo admin)
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
            '''UPDATE implementos 
               SET implemento = ?, descripcion = ?, disponibilidad = ?, 
                   categoria = ?, imagen_url = ?, fecha_actualizacion = CURRENT_TIMESTAMP
               WHERE id = ?''',
            (implemento, descripcion, disponibilidad, categoria, imagen_url, id)
        )
        conn.commit()
        flash('Implemento actualizado exitosamente.', 'success')
    except Exception as e:
        flash(f'Error al actualizar implemento: {str(e)}', 'error')
    finally:
        conn.close()

    return redirect(url_for('catalogo.catalogo'))

# Eliminar implemento (solo admin)
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
            'SELECT COUNT(*) as count FROM prestamos WHERE fk_implemento = ? AND fecha_devolucion IS NULL',
            (id,)
        ).fetchone()

        if prestamos_activos['count'] > 0:
            flash('No se puede eliminar el implemento porque tiene préstamos activos.', 'error')
            return redirect(url_for('catalogo.catalogo'))

        conn.execute('DELETE FROM implementos WHERE id = ?', (id,))
        conn.commit()
        flash('Implemento eliminado exitosamente.', 'success')
        
    except Exception as e:
        flash(f'Error al eliminar implemento: {str(e)}', 'error')
    finally:
        conn.close()

    return redirect(url_for('catalogo.catalogo'))