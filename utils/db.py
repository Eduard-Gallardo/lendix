import sqlite3
import os

def get_db_connection():
    conn = sqlite3.connect('models/database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    with conn:
        # Tabla Usuarios
        conn.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                telefono TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            )
        ''')
        
        # Tabla catalogo (actualizada con campo de imagen)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS catalogo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                implemento TEXT NOT NULL,
                descripcion TEXT NOT NULL,
                disponibilidad INTEGER NOT NULL,
                imagen_url TEXT,
                categoria TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla prestamos
        conn.execute('''
            CREATE TABLE IF NOT EXISTS prestamos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fk_usuario INTEGER NOT NULL,
                fk_modelo INTEGER NOT NULL,
                fecha_prestamo TEXT NOT NULL,
                fecha_devolucion TEXT,
                nombre TEXT NOT NULL,
                instructor TEXT,
                jornada TEXT,
                ambiente TEXT,
                FOREIGN KEY (fk_usuario) REFERENCES usuarios(id),
                FOREIGN KEY (fk_modelo) REFERENCES catalogo(id)                
            )
        ''')

        # Tabla reservas
        conn.execute('''
            CREATE TABLE IF NOT EXISTS reservas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fk_usuario INTEGER NOT NULL,
                fk_implemento INTEGER NOT NULL,
                fecha_reserva TIMESTAMP NOT NULL,
                fecha_inicio TIMESTAMP NOT NULL,
                fecha_fin TIMESTAMP NOT NULL,
                nombre TEXT NOT NULL,
                lugar TEXT,
                estado TEXT DEFAULT 'pendiente',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (fk_usuario) REFERENCES usuarios(id),
                FOREIGN KEY (fk_implemento) REFERENCES catalogo(id)
            )
        ''')
    conn.close()