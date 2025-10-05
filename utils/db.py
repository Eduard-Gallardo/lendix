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