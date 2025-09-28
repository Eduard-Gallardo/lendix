import sqlite3
import os
from datetime import datetime, timedelta

def get_db_connection():
    """Obtener conexión a la base de datos"""
    # Asegurar que la carpeta models existe
    os.makedirs('models', exist_ok=True)
    conn = sqlite3.connect('models/database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Inicializar la base de datos con las tablas necesarias"""
    conn = get_db_connection()
    with conn:
        # Tabla Usuarios - Actualizada con nuevo campo rol
        conn.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                telefono TEXT NOT NULL UNIQUE,
                rol TEXT NOT NULL CHECK(rol IN ('aprendiz', 'instructor', 'externo', 'admin')) DEFAULT 'aprendiz',
                password TEXT NOT NULL,
                activo BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla catálogo - Actualizada con nuevos campos
        conn.execute('''
            CREATE TABLE IF NOT EXISTS catalogo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                implemento TEXT NOT NULL,
                descripcion TEXT NOT NULL,
                disponibilidad INTEGER NOT NULL DEFAULT 0,
                imagen_url TEXT,
                categoria TEXT,
                habilitado BOOLEAN DEFAULT 1,
                requiere_autorizacion BOOLEAN DEFAULT 1, -- Si requiere autorización de instructor
                solo_instructores BOOLEAN DEFAULT 0,    -- Si es exclusivo para instructores
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla préstamos - Actualizada con mejor estructura
        conn.execute('''
            CREATE TABLE IF NOT EXISTS prestamos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fk_usuario INTEGER NOT NULL,           -- Usuario que registra el préstamo
                fk_modelo INTEGER NOT NULL,            -- Implemento prestado
                fecha_prestamo TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                fecha_devolucion TIMESTAMP,            -- NULL mientras esté activo
                fecha_devolucion_estimada TIMESTAMP NOT NULL,
                cantidad INTEGER NOT NULL DEFAULT 1,
                estado TEXT NOT NULL CHECK(estado IN ('pendiente', 'aprobado', 'rechazado', 'activo', 'completado', 'cancelado')) DEFAULT 'pendiente',
                nombre TEXT NOT NULL,                  -- Nombre del prestatario (puede ser diferente al usuario)
                instructor TEXT,                       -- Nombre del instructor
                jornada TEXT,                         -- Jornada (Mañana, Tarde, Noche)
                ambiente TEXT,                        -- Número de ambiente
                instructor_autorizador INTEGER,       -- ID del instructor que autoriza (NULL si no requiere)
                observaciones TEXT,
                motivo_rechazo TEXT,                  -- Motivo si fue rechazado
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (fk_usuario) REFERENCES usuarios(id),
                FOREIGN KEY (fk_modelo) REFERENCES catalogo(id),
                FOREIGN KEY (instructor_autorizador) REFERENCES usuarios(id)
            )
        ''')

        # Tabla reservas - Actualizada
        conn.execute('''
            CREATE TABLE IF NOT EXISTS reservas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fk_usuario INTEGER NOT NULL,
                fk_implemento INTEGER NOT NULL,
                fecha_reserva TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                fecha_inicio TIMESTAMP NOT NULL,
                fecha_fin TIMESTAMP NOT NULL,
                nombre TEXT NOT NULL,
                lugar TEXT,
                estado TEXT NOT NULL CHECK(estado IN ('pendiente', 'aprobada', 'rechazada', 'activa', 'completada', 'cancelada')) DEFAULT 'pendiente',
                instructor_autorizador INTEGER,
                motivo_rechazo TEXT,
                observaciones TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (fk_usuario) REFERENCES usuarios(id),
                FOREIGN KEY (fk_implemento) REFERENCES catalogo(id),
                FOREIGN KEY (instructor_autorizador) REFERENCES usuarios(id)
            )
        ''')
        
        # Tabla de notificaciones para instructores
        conn.execute('''
            CREATE TABLE IF NOT EXISTS notificaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fk_instructor INTEGER NOT NULL,       -- ID del instructor
                tipo TEXT NOT NULL CHECK(tipo IN ('prestamo', 'reserva')),
                fk_referencia INTEGER NOT NULL,       -- ID del préstamo o reserva
                mensaje TEXT NOT NULL,
                leida BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (fk_instructor) REFERENCES usuarios(id)
            )
        ''')
        
def seed_sample_data():
    """Agregar datos de ejemplo"""
    conn = get_db_connection()
    with conn:
        # Verificar si ya hay datos
        existing_users = conn.execute('SELECT COUNT(*) as count FROM usuarios').fetchone()
        if existing_users['count'] > 0:
            return  # Ya hay datos
            
        from werkzeug.security import generate_password_hash
        
        # Crear usuarios de ejemplo
        admin_password = generate_password_hash('admin123')
        instructor_password = generate_password_hash('instructor123')
        aprendiz_password = generate_password_hash('aprendiz123')
        externo_password = generate_password_hash('externo123')
        
        conn.execute('''
            INSERT INTO usuarios (nombre, email, telefono, rol, password) VALUES
            ('Admin Sistema', 'Eduard@gmail.com', '3001234567', 'admin', ?),
            ('Carlos Instructor', 'instructor@sena.edu.co', '3001234568', 'instructor', ?),
            ('María Aprendiz', 'aprendiz@sena.edu.co', '3001234569', 'aprendiz', ?),
            ('Juan Externo', 'externo@example.com', '3001234570', 'externo', ?)
        ''', (admin_password, instructor_password, aprendiz_password, externo_password))
        
        # Crear implementos de ejemplo
        conn.execute('''
            INSERT INTO catalogo (implemento, descripcion, disponibilidad, categoria, requiere_autorizacion, solo_instructores) VALUES
            ('Laptop Dell Inspiron', 'Computadora portátil para desarrollo', 5, 'Computadores', 1, 0),
            ('Mouse Inalámbrico', 'Mouse óptico inalámbrico', 20, 'Mouses', 0, 0),
            ('Teclado Mecánico', 'Teclado mecánico RGB', 10, 'Teclados', 1, 0),
            ('Manual Técnico Avanzado', 'Manual exclusivo para instructores', 3, 'Libros', 0, 1),
            ('Equipo de Laboratorio', 'Equipamiento especializado', 2, 'Otros', 1, 1),
            ('Calculadora Científica', 'Calculadora para cálculos complejos', 15, 'Otros', 0, 0)
        ''')
        