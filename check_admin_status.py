import sqlite3
from database import get_db

conn = get_db()
cursor = conn.cursor()

try:
    cursor.execute("SELECT status FROM users WHERE username = 'admin1'")
    status = cursor.fetchone()
    if status:
        print(f"El estado actual de admin1 es: {status[0]}")
    else:
        print("Usuario admin1 no encontrado.")
except Exception as e:
    print(f"Error al verificar el estado: {e}")
finally:
    conn.close()
