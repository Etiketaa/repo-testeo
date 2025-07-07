import sqlite3

import os

# Obtener la ruta absoluta del directorio del script actual
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Definir la ruta absoluta de la base de datos
import os

# Obtener la ruta absoluta del directorio del script actual
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Definir la ruta absoluta de la base de datos
DATABASE = os.path.join(BASE_DIR, 'pos_system.db')

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row # Esto permite acceder a las columnas por nombre
    return conn

def initialize_database():
    conn = get_db()
    cursor = conn.cursor()
    
    # Crear tabla de roles
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    """)

    # Crear tabla de usuarios
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role_id INTEGER,
            status TEXT DEFAULT 'pending' NOT NULL, -- 'pending', 'approved', 'rejected'
            FOREIGN KEY (role_id) REFERENCES roles (id)
        )
    """)
    
    # Añadir columna 'status' si no existe (para bases de datos existentes)
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'pending' NOT NULL")
    except sqlite3.OperationalError:
        # La columna ya existe, no hacer nada
        pass

    # Crear tabla de categorías
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    """)

    # Crear tabla de productos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            cost_price REAL,
            quantity INTEGER NOT NULL,
            supplier TEXT,
            category_id INTEGER,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories (id)
        )
    """)

    # Crear tabla de imágenes de productos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS product_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            image_data TEXT NOT NULL, -- Base64 encoded image
            FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE
        )
    """)

    # Crear tabla de ventas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            total_amount REAL NOT NULL,
            sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    # Crear tabla de ítems de venta
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sale_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            price_per_unit REAL NOT NULL,
            FOREIGN KEY (sale_id) REFERENCES sales (id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    """)

    # Crear tabla de movimientos de inventario
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            quantity_change INTEGER NOT NULL,
            reason TEXT,
            movement_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    """)

    conn.commit()
    conn.close()

if __name__ == '__main__':
    initialize_database()
    print("Base de datos inicializada.")
