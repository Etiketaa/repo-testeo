import sqlite3
import hashlib
from database import get_db, initialize_database

def seed_data():
    conn = get_db()
    cursor = conn.cursor()

    try:
        # Insertar roles
        roles = [('admin',), ('depo',), ('venta',)]
        for role_name in roles:
            try:
                cursor.execute("INSERT INTO roles (name) VALUES (?)", role_name)
                print(f"Rol '{role_name[0]}' insertado o ya existente.")
            except sqlite3.IntegrityError:
                print(f"Rol '{role_name[0]}' ya existe.")

        # Obtener IDs de los roles
        cursor.execute("SELECT id FROM roles WHERE name = 'admin'")
        admin_role_id = cursor.fetchone()[0]
        
        cursor.execute("SELECT id FROM roles WHERE name = 'depo'")
        depo_role_id = cursor.fetchone()[0]

        cursor.execute("SELECT id FROM roles WHERE name = 'venta'")
        venta_role_id = cursor.fetchone()[0]

        # Crear usuarios
        users = [
            ('admin1', 'admin1', admin_role_id, 'approved'),
            ('admin2', 'admin2', admin_role_id, 'approved'),
            ('admin3', 'admin3', admin_role_id, 'approved'),
            ('depo1', 'depo1', depo_role_id, 'approved'),
            ('venta1', 'venta1', venta_role_id, 'approved'),
        ]

        for username, password, role_id, status in users:
            hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
            try:
                cursor.execute("INSERT INTO users (username, password, role_id, status) VALUES (?, ?, ?, ?)",
                               (username, hashed_password, role_id, status))
                print(f"Usuario '{username}' creado con estado '{status}'.")
            except sqlite3.IntegrityError:
                print(f"Usuario '{username}' ya existe.")

        # Insertar categorías
        categories = [('Electrónica',), ('Ropa',), ('Libros',), ('Alimentos',)]
        for category_name in categories:
            try:
                cursor.execute("INSERT INTO categories (name) VALUES (?)", category_name)
                print(f"Categoría '{category_name[0]}' insertada.")
            except sqlite3.IntegrityError:
                print(f"Categoría '{category_name[0]}' ya existe.")

        conn.commit()

    except sqlite3.Error as e:
        print(f"Ocurrió un error: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    initialize_database() # Asegurarse de que las tablas existen
    seed_data()
    print("Base de datos poblada con datos iniciales.")
