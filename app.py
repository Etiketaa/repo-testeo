from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import hashlib
import base64
from database import get_db
from functools import wraps
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here' # ¡Cambia esto por una clave secreta real y segura!

# Decorador para requerir inicio de sesión
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Por favor, inicia sesión para acceder a esta página.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Decorador para requerir un rol específico
def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'username' not in session:
                flash('Por favor, inicia sesión para acceder a esta página.', 'warning')
                return redirect(url_for('login'))
            if session.get('role') not in allowed_roles:
                flash('No tienes permiso para acceder a esta página.', 'danger')
                return redirect(url_for('dashboard')) # O a una página de error de acceso denegado
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT u.password, r.name, u.status, u.id FROM users u JOIN roles r ON u.role_id = r.id WHERE u.username = ?", (username,))
        user_data = cursor.fetchone()
        conn.close()

        if user_data:
            stored_password, role, status, user_id = user_data
            hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()

            if hashed_password == stored_password:
                if status == 'approved':
                    session['username'] = username
                    session['role'] = role
                    session['user_id'] = user_id # Guardar user_id en la sesión
                    flash('Inicio de sesión exitoso!', 'success')
                    return redirect(url_for('dashboard'))
                elif status == 'pending':
                    flash('Tu cuenta está pendiente de aprobación por un administrador.', 'warning')
                else: # rejected
                    flash('Tu cuenta ha sido rechazada. Contacta al administrador.', 'danger')
            else:
                flash('Contraseña incorrecta.', 'danger')
        else:
            flash('Usuario no encontrado.', 'danger')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        role_name = request.form['role']

        if password != confirm_password:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template('register.html')

        conn = get_db()
        cursor = conn.cursor()
        
        # Obtener role_id
        cursor.execute("SELECT id FROM roles WHERE name = ?", (role_name,))
        role_data = cursor.fetchone()
        if not role_data:
            flash('Rol inválido.', 'danger')
            conn.close()
            return render_template('register.html')
        role_id = role_data[0]

        hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
        
        try:
            cursor.execute("INSERT INTO users (username, password, role_id, status) VALUES (?, ?, ?, ?)",
                           (username, hashed_password, role_id, 'pending'))
            conn.commit()
            flash('Registro exitoso. Tu cuenta está pendiente de aprobación.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('El nombre de usuario ya existe.', 'danger')
        except Exception as e:
            flash(f'Ocurrió un error al registrar el usuario: {e}', 'danger')
        finally:
            conn.close()

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    session.pop('user_id', None)
    flash('Has cerrado sesión.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', username=session['username'], role=session['role'])

# Rutas de administración de usuarios
@app.route('/admin/users')
@login_required
@role_required(['admin'])
def admin_users():
    conn = get_db()
    cursor = conn.cursor()
    users = cursor.execute("SELECT u.id, u.username, r.name as role, u.status FROM users u JOIN roles r ON u.role_id = r.id").fetchall()
    conn.close()
    return render_template('admin_users.html', users=users)

@app.route('/admin/users/<int:user_id>/status', methods=['POST'])
@login_required
@role_required(['admin'])
def update_user_status(user_id):
    status = request.form['status']
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET status = ? WHERE id = ?", (status, user_id))
        conn.commit()
        flash(f'Estado del usuario actualizado a {status}.', 'success')
    except Exception as e:
        flash(f'Error al actualizar el estado del usuario: {e}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('admin_users'))

# API para Categorías
@app.route('/api/categories', methods=['GET'])
def get_categories():
    conn = get_db()
    cursor = conn.cursor()
    categories = cursor.execute("SELECT id, name FROM categories").fetchall()
    conn.close()
    return jsonify([dict(category) for category in categories])

@app.route('/api/categories', methods=['POST'])
@login_required
@role_required(['admin', 'depo'])
def add_category():
    data = request.get_json()
    name = data.get('name')

    if not name:
        return jsonify({'error': 'El nombre de la categoría es obligatorio.'}), 400

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO categories (name) VALUES (?)", (name,))
        conn.commit()
        return jsonify({'message': 'Categoría añadida correctamente.', 'id': cursor.lastrowid}), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': f'La categoría \'{name}\' ya existe.'}), 409
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/categories/<int:category_id>', methods=['PUT'])
@login_required
@role_required(['admin', 'depo'])
def update_category(category_id):
    data = request.get_json()
    name = data.get('name')

    if not name:
        return jsonify({'error': 'El nombre de la categoría es obligatorio.'}), 400

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE categories SET name = ? WHERE id = ?", (name, category_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'error': 'Categoría no encontrada.'}), 404
        return jsonify({'message': 'Categoría actualizada correctamente.'}), 200
    except sqlite3.IntegrityError:
        return jsonify({'error': f'La categoría \'{name}\' ya existe.'}), 409
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/categories/<int:category_id>', methods=['DELETE'])
@login_required
@role_required(['admin', 'depo'])
def delete_category(category_id):
    conn = get_db()
    cursor = conn.cursor()
    try:
        # Opcional: Actualizar productos asociados a NULL antes de eliminar la categoría
        cursor.execute("UPDATE products SET category_id = NULL WHERE category_id = ?", (category_id,))
        cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'error': 'Categoría no encontrada.'}), 404
        return jsonify({'message': 'Categoría eliminada correctamente.'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# API para Productos
@app.route('/api/products', methods=['GET'])
def get_products():
    conn = get_db()
    cursor = conn.cursor()
    search_term = request.args.get('search', '')
    category_id = request.args.get('category_id', type=int)

    query = "SELECT p.id, p.sku, p.name, p.description, p.price, p.cost_price, p.quantity, p.supplier, c.name as category_name FROM products p LEFT JOIN categories c ON p.category_id = c.id WHERE 1=1"
    params = []

    if search_term:
        query += " AND (p.name LIKE ? OR p.sku LIKE ?)"
        params.extend([f'%{search_term}%', f'%{search_term}%'])
    if category_id:
        query += " AND p.category_id = ?"
        params.append(category_id)

    products = cursor.execute(query, params).fetchall()
    
    # Obtener imágenes para cada producto
    products_with_images = []
    for product in products:
        product_dict = dict(product)
        image_cursor = conn.cursor()
        images = image_cursor.execute("SELECT image_data FROM product_images WHERE product_id = ?", (product['id'],)).fetchall()
        product_dict['images'] = [img['image_data'] for img in images]
        products_with_images.append(product_dict)

    conn.close()
    return jsonify(products_with_images)

def generate_sku(name):
    prefix = ''.join(word[0] for word in name.split() if word).upper()
    if not prefix: # Fallback if name is empty or only spaces
        prefix = "PROD"
    return f"{prefix}-{random.randint(1000, 9999)}"

@app.route('/api/products', methods=['POST'])
@login_required
@role_required(['admin', 'depo'])
def add_product():
    data = request.get_json()
    sku = data.get('sku')
    name = data.get('name')
    description = data.get('description')
    price = data.get('price')
    cost_price = data.get('cost_price')
    quantity = data.get('quantity')
    supplier = data.get('supplier')
    category_id = data.get('category_id')
    images = data.get('images', []) # Lista de strings base64

    if not all([name, price, quantity]): # SKU ya no es obligatorio en el formulario
        return jsonify({'error': 'Nombre, precio y cantidad son obligatorios.'}), 400

    if not sku: # Generar SKU si no se proporciona
        sku = generate_sku(name)

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO products (sku, name, description, price, cost_price, quantity, supplier, category_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                       (sku, name, description, price, cost_price, quantity, supplier, category_id))
        product_id = cursor.lastrowid

        for img_data in images:
            cursor.execute("INSERT INTO product_images (product_id, image_data) VALUES (?, ?)", (product_id, img_data))
        
        # Log initial stock movement
        cursor.execute("INSERT INTO inventory_movements (product_id, quantity_change, reason) VALUES (?, ?, ?)",
                       (product_id, quantity, "Initial Stock"))

        conn.commit()
        return jsonify({'message': 'Producto añadido correctamente.', 'id': product_id}), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': f'El SKU \'{sku}\' ya existe.'}), 409
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/products/<int:product_id>', methods=['PUT'])
@login_required
@role_required(['admin', 'depo'])
def update_product(product_id):
    data = request.get_json()
    name = data.get('name')
    description = data.get('description')
    price = data.get('price')
    cost_price = data.get('cost_price')
    quantity = data.get('quantity')
    supplier = data.get('supplier')
    category_id = data.get('category_id')
    images = data.get('images', [])

    if not all([name, price, quantity]):
        return jsonify({'error': 'Nombre, precio y cantidad son obligatorios.'}), 400

    conn = get_db()
    cursor = conn.cursor()
    try:
        # Get old quantity for logging movement
        cursor.execute("SELECT quantity FROM products WHERE id = ?", (product_id,))
        old_quantity = cursor.fetchone()[0]
        quantity_change = int(quantity) - old_quantity

        cursor.execute("UPDATE products SET name=?, description=?, price=?, cost_price=?, quantity=?, supplier=?, category_id=?, last_updated=CURRENT_TIMESTAMP WHERE id=?",
                       (name, description, price, cost_price, quantity, supplier, category_id, product_id))
        
        # Update images: delete old and insert new ones
        cursor.execute("DELETE FROM product_images WHERE product_id = ?", (product_id,))
        for img_data in images:
            cursor.execute("INSERT INTO product_images (product_id, image_data) VALUES (?, ?)", (product_id, img_data))

        # Log inventory movement if quantity changed
        if quantity_change != 0:
            reason = "Ajuste de Stock" if quantity_change > 0 else "Ajuste de Stock (Reducción)"
            cursor.execute("INSERT INTO inventory_movements (product_id, quantity_change, reason) VALUES (?, ?, ?)",
                           (product_id, quantity_change, reason))

        conn.commit()
        return jsonify({'message': 'Producto actualizado correctamente.'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/products/<int:product_id>', methods=['DELETE'])
@login_required
@role_required(['admin', 'depo'])
def delete_product(product_id):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM product_images WHERE product_id = ?", (product_id,))
        cursor.execute("DELETE FROM inventory_movements WHERE product_id = ?", (product_id,))
        cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'error': 'Producto no encontrado.'}), 404
        return jsonify({'message': 'Producto eliminado correctamente.'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# API para Ventas
@app.route('/api/sales', methods=['POST'])
@login_required
@role_required(['admin', 'venta'])
def process_sale():
    data = request.get_json()
    cart_items = data.get('cart')
    total_amount = data.get('total')
    user_id = session.get('user_id') # Obtener user_id de la sesión

    if not cart_items or not total_amount or not user_id:
        return jsonify({'error': 'Datos de venta incompletos o usuario no autenticado.'}), 400

    conn = get_db()
    cursor = conn.cursor()
    try:
        # Insertar la venta principal
        cursor.execute("INSERT INTO sales (user_id, total_amount) VALUES (?, ?)", (user_id, total_amount))
        sale_id = cursor.lastrowid

        # Insertar ítems de la venta y actualizar el inventario
        for item in cart_items:
            product_id = item.get('id')
            quantity = item.get('quantity')
            price_per_unit = item.get('price')

            cursor.execute("INSERT INTO sale_items (sale_id, product_id, quantity, price_per_unit) VALUES (?, ?, ?, ?)",
                           (sale_id, product_id, quantity, price_per_unit))
            
            # Actualizar cantidad de producto en inventario
            cursor.execute("UPDATE products SET quantity = quantity - ? WHERE id = ?", (quantity, product_id))
            
            # Registrar movimiento de inventario
            cursor.execute("INSERT INTO inventory_movements (product_id, quantity_change, reason) VALUES (?, ?, ?)",
                           (product_id, -quantity, "Venta"))

        conn.commit()
        return jsonify({'message': 'Venta procesada correctamente.', 'sale_id': sale_id}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/sales', methods=['GET'])
@login_required
@role_required(['admin', 'venta'])
def get_sales_history():
    conn = get_db()
    cursor = conn.cursor()
    sales = cursor.execute("""
        SELECT s.id, u.username, s.total_amount, s.sale_date
        FROM sales s
        JOIN users u ON s.user_id = u.id
        ORDER BY s.sale_date DESC
    """).fetchall()
    conn.close()
    return jsonify([dict(sale) for sale in sales])

@app.route('/api/sales/<int:sale_id>/items', methods=['GET'])
@login_required
@role_required(['admin', 'venta'])
def get_sale_items(sale_id):
    conn = get_db()
    cursor = conn.cursor()
    items = cursor.execute("""
        SELECT p.name, si.quantity, si.price_per_unit
        FROM sale_items si
        JOIN products p ON si.product_id = p.id
        WHERE si.sale_id = ?
    """, (sale_id,)).fetchall()
    conn.close()
    return jsonify([dict(item) for item in items])

if __name__ == '__main__':
    app.run(debug=True)