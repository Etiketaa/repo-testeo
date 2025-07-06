import sqlite3
from database import get_db

conn = get_db()
cursor = conn.cursor()

try:
    cursor.execute("UPDATE users SET status = 'approved' WHERE username = 'admin1'")
    conn.commit()
    print("Usuario 'admin1' actualizado a estado 'approved'.")
except Exception as e:
    print(f"Error al actualizar el usuario: {e}")
finally:
    conn.close()
