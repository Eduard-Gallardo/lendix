import sqlite3
import os

def get_db_connection():
    conn = sqlite3.connect('models/database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    with conn:
        # Tabla Usuarios (admin, instructor y funcionario)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                telefono TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                rol TEXT DEFAULT 'funcionario' CHECK(rol IN ('admin', 'instructor', 'funcionario')),
                activo BOOLEAN DEFAULT 1,
                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla implementos (antes catálogo)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS implementos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                implemento TEXT NOT NULL,
                descripcion TEXT NOT NULL,
                disponibilidad INTEGER NOT NULL DEFAULT 0,
                categoria TEXT,
                imagen_url TEXT,
                estado TEXT DEFAULT 'Bueno' CHECK(estado IN ('Bueno', 'Desgaste notable', 'Dañado')),
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla prestamos mejorada
        conn.execute('''
            CREATE TABLE IF NOT EXISTS prestamos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fk_usuario INTEGER NOT NULL,
                fk_implemento INTEGER NOT NULL,
                tipo_prestamo TEXT NOT NULL CHECK(tipo_prestamo IN ('individual', 'multiple')),
                nombre_prestatario TEXT NOT NULL,
                ficha TEXT,
                ambiente TEXT,
                horario TEXT,
                instructor TEXT,
                jornada TEXT,
                fecha_prestamo TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fecha_devolucion TIMESTAMP,
                novedad TEXT DEFAULT 'Ninguna',
                estado_implemento_devolucion TEXT DEFAULT 'Bueno' CHECK(estado_implemento_devolucion IN ('Bueno', 'Desgaste notable', 'Dañado')),
                observaciones TEXT,
                FOREIGN KEY (fk_usuario) REFERENCES usuarios(id),
                FOREIGN KEY (fk_implemento) REFERENCES implementos(id)
            )
        ''')
        
        # Tabla notificaciones para el dashboard del admin
        conn.execute('''
            CREATE TABLE IF NOT EXISTS notificaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT NOT NULL CHECK(tipo IN ('prestamo_individual', 'prestamo_multiple', 'devolucion', 'implemento_nuevo')),
                titulo TEXT NOT NULL,
                mensaje TEXT NOT NULL,
                fk_usuario INTEGER,
                fk_prestamo INTEGER,
                leida BOOLEAN DEFAULT 0,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (fk_usuario) REFERENCES usuarios(id),
                FOREIGN KEY (fk_prestamo) REFERENCES prestamos(id)
            )
        ''')
        
        # Tabla historial para auditoría
        conn.execute('''
            CREATE TABLE IF NOT EXISTS historial_acciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fk_usuario INTEGER NOT NULL,
                accion TEXT NOT NULL,
                detalle TEXT,
                ip_address TEXT,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (fk_usuario) REFERENCES usuarios(id)
            )
        ''')
        
        
    conn.close()

def crear_admin_inicial():
    """Crea un usuario admin inicial si no existe"""
    from werkzeug.security import generate_password_hash
    
    conn = get_db_connection()
    try:
        # Verificar si ya existe un admin
        admin = conn.execute(
            "SELECT * FROM usuarios WHERE rol = 'admin'"
        ).fetchone()
        
        if not admin:
            # Crear admin por defecto
            conn.execute('''
                INSERT INTO usuarios (nombre, email, telefono, password, rol, activo)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                'Administrador',
                'Eduard@gmail.com',
                '3000000000',
                generate_password_hash('admin123'),
                'admin',
                1
            ))
            conn.commit()
            print("Usuario admin creado exitosamente")
    except Exception as e:
        print(f"Error al crear admin: {e}")
    finally:
        conn.close()

def migrar_base_datos():
    """Migra la base de datos existente para corregir inconsistencias"""
    conn = get_db_connection()
    try:
        # Verificar si la tabla prestamos existe y tiene las columnas correctas
        cursor = conn.execute("PRAGMA table_info(prestamos)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Agregar columnas faltantes si no existen
        if 'instructor' not in columns:
            conn.execute('''
                ALTER TABLE prestamos ADD COLUMN instructor TEXT
            ''')
            print("Columna instructor agregada a prestamos")
        
        if 'jornada' not in columns:
            conn.execute('''
                ALTER TABLE prestamos ADD COLUMN jornada TEXT
            ''')
            print("Columna jornada agregada a prestamos")
        
        if 'estado_implemento_devolucion' not in columns:
            conn.execute('''
                ALTER TABLE prestamos ADD COLUMN estado_implemento_devolucion TEXT DEFAULT 'Bueno'
            ''')
            print("Columna estado_implemento_devolucion agregada a prestamos")
        
        if 'observaciones' not in columns:
            conn.execute('''
                ALTER TABLE prestamos ADD COLUMN observaciones TEXT
            ''')
            print("Columna observaciones agregada a prestamos")
        
        # Eliminar tablas de permisos si existen
        try:
            conn.execute('DROP TABLE IF EXISTS permisos_ambientes')
            conn.execute('DROP TABLE IF EXISTS permisos_aprendices')
            print("Tablas de permisos eliminadas")
        except Exception as e:
            print(f"Error al eliminar tablas de permisos: {e}")
        
        # Actualizar constraint de estado si es necesario
        try:
            # Actualizar estados a los nuevos valores
            conn.execute('''
                UPDATE implementos SET estado = 'Bueno' 
                WHERE estado NOT IN ('Bueno', 'Desgaste notable', 'Dañado')
            ''')
            
            conn.execute('''
                UPDATE prestamos SET estado_implemento_devolucion = 'Bueno' 
                WHERE estado_implemento_devolucion NOT IN ('Bueno', 'Desgaste notable', 'Dañado')
                OR estado_implemento_devolucion IS NULL
            ''')
            
            conn.commit()
            print("Migración de base de datos completada exitosamente")
            
        except Exception as e:
            print(f"Error durante la migración: {e}")
            
    except Exception as e:
        print(f"Error al migrar base de datos: {e}")
    finally:
        conn.close()

def reordenar_ids_implementos():
    """Reordena los IDs de los implementos para que sean consecutivos"""
    conn = get_db_connection()
    try:
        # Obtener todos los implementos ordenados por ID actual
        implementos = conn.execute('SELECT * FROM implementos ORDER BY id').fetchall()
        
        if not implementos:
            return
        
        # Crear tabla temporal con los mismos datos
        conn.execute('''
            CREATE TEMPORARY TABLE implementos_temp (
                id INTEGER PRIMARY KEY,
                implemento TEXT NOT NULL,
                descripcion TEXT NOT NULL,
                disponibilidad INTEGER NOT NULL DEFAULT 0,
                categoria TEXT,
                imagen_url TEXT,
                estado TEXT DEFAULT 'Bueno' CHECK(estado IN ('Bueno', 'Desgaste notable', 'Dañado')),
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insertar datos con nuevos IDs consecutivos
        nuevo_id = 1
        for implemento in implementos:
            conn.execute('''
                INSERT INTO implementos_temp (id, implemento, descripcion, disponibilidad, categoria, imagen_url, estado, fecha_creacion, fecha_actualizacion)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                nuevo_id,
                implemento['implemento'],
                implemento['descripcion'],
                implemento['disponibilidad'],
                implemento['categoria'],
                implemento['imagen_url'],
                implemento['estado'],
                implemento['fecha_creacion'],
                implemento['fecha_actualizacion']
            ))
            
            # Actualizar referencias en préstamos si el ID cambió
            if implemento['id'] != nuevo_id:
                conn.execute('''
                    UPDATE prestamos SET fk_implemento = ? WHERE fk_implemento = ?
                ''', (nuevo_id, implemento['id']))
            
            nuevo_id += 1
        
        # Eliminar tabla original y renombrar la temporal
        conn.execute('DROP TABLE implementos')
        conn.execute('ALTER TABLE implementos_temp RENAME TO implementos')
        
        # Recrear la secuencia de autoincremento
        conn.execute('DELETE FROM sqlite_sequence WHERE name = "implementos"')
        conn.execute('INSERT INTO sqlite_sequence (name, seq) VALUES ("implementos", ?)', (nuevo_id - 1,))
        
        conn.commit()
        print(f"IDs de implementos reordenados exitosamente. Nuevo último ID: {nuevo_id - 1}")
        
    except Exception as e:
        print(f"Error al reordenar IDs: {e}")
        conn.rollback()
    finally:
        conn.close()

def obtener_siguiente_id_consecutivo():
    """Obtiene el siguiente ID consecutivo para implementos"""
    conn = get_db_connection()
    try:
        # Obtener el último ID actual
        resultado = conn.execute('SELECT MAX(id) as max_id FROM implementos').fetchone()
        ultimo_id = resultado['max_id'] if resultado['max_id'] else 0
        
        # Verificar si hay gaps en los IDs
        total_implementos = conn.execute('SELECT COUNT(*) as count FROM implementos').fetchone()['count']
        
        if ultimo_id != total_implementos:
            # Hay gaps, reordenar
            reordenar_ids_implementos()
            ultimo_id = conn.execute('SELECT MAX(id) as max_id FROM implementos').fetchone()['max_id']
        
        return ultimo_id + 1
        
    except Exception as e:
        print(f"Error al obtener siguiente ID: {e}")
        return 1
    finally:
        conn.close()