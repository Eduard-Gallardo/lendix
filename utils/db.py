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
                activo BOOLEAN DEFAULT 0,
                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla catalogo
        conn.execute('''
            CREATE TABLE IF NOT EXISTS catalogo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                descripcion TEXT NOT NULL,
                cantidad_disponible INTEGER NOT NULL DEFAULT 0,
                cantidad_total INTEGER NOT NULL DEFAULT 0,
                imagen_url TEXT,
                categoria TEXT,
                estado TEXT DEFAULT 'disponible' CHECK(estado IN ('disponible', 'no_disponible', 'mantenimiento')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla prestamos (simplificada para instructor)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS prestamos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fk_usuario INTEGER NOT NULL,
                fk_item INTEGER NOT NULL,
                cantidad INTEGER DEFAULT 1,
                fecha_prestamo TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fecha_devolucion_estimada TEXT NOT NULL,
                fecha_devolucion_real TIMESTAMP,
                estado TEXT DEFAULT 'activo' CHECK(estado IN ('activo', 'devuelto', 'vencido', 'renovado')),
                observaciones TEXT,
                aprobado_por INTEGER,
                FOREIGN KEY (fk_usuario) REFERENCES usuarios(id),
                FOREIGN KEY (fk_item) REFERENCES catalogo(id),
                FOREIGN KEY (aprobado_por) REFERENCES usuarios(id)
            )
        ''')
        
        # Tabla notificaciones para el dashboard del admin
        conn.execute('''
            CREATE TABLE IF NOT EXISTS notificaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT NOT NULL CHECK(tipo IN ('prestamo_nuevo', 'devolucion', 'vencimiento', 'registro_usuario')),
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

def migrate_db():
    """
    Función para migrar datos existentes al nuevo esquema
    Elimina referencias a 'aprendiz' y actualiza la estructura
    """
    conn = get_db_connection()
    try:
        with conn:
            # Verificar si existe la columna tipo_usuario y migrar a rol
            cursor = conn.execute("PRAGMA table_info(usuarios)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'tipo_usuario' in columns and 'rol' not in columns:
                # Crear tabla temporal con nueva estructura
                conn.execute('''
                    CREATE TABLE usuarios_new (
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
                
                # Migrar datos (convertir aprendices a funcionarios)
                conn.execute('''
                    INSERT INTO usuarios_new (id, nombre, email, telefono, password, rol, activo, fecha_registro)
                    SELECT id, nombre, email, telefono, password, 
                           CASE 
                               WHEN tipo_usuario = 'admin' THEN 'admin'
                               WHEN tipo_usuario = 'instructor' THEN 'instructor'
                               WHEN tipo_usuario = 'funcionario' THEN 'funcionario'
                               ELSE 'funcionario'
                           END as rol,
                           activo, fecha_registro
                    FROM usuarios
                ''')
                
                # Reemplazar tabla
                conn.execute('DROP TABLE usuarios')
                conn.execute('ALTER TABLE usuarios_new RENAME TO usuarios')
            
            # Actualizar tabla catalogo si es necesario
            cursor = conn.execute("PRAGMA table_info(catalogo)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'implemento' in columns and 'nombre' not in columns:
                conn.execute('ALTER TABLE catalogo RENAME COLUMN implemento TO nombre')
            
            if 'disponibilidad' in columns and 'cantidad_disponible' not in columns:
                conn.execute('ALTER TABLE catalogo ADD COLUMN cantidad_disponible INTEGER DEFAULT 0')
                conn.execute('ALTER TABLE catalogo ADD COLUMN cantidad_total INTEGER DEFAULT 0')
                conn.execute('UPDATE catalogo SET cantidad_disponible = disponibilidad, cantidad_total = disponibilidad')
            
            print("Migración completada exitosamente")
            
    except Exception as e:
        print(f"Error durante la migración: {e}")
    finally:
        conn.close()