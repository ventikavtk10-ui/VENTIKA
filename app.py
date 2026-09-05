import os
import uuid
import sqlite3
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
import stripe
import requests

load_dotenv()  # Carga variables desde un archivo .env si existe

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "ventika_super_secret_key_change_in_production")

# Configuración de subida de imágenes
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Configuración de Stripe (Modo Sandbox/Pruebas - reemplaza con tus llaves reales via variables de entorno)
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY', 'sk_test_51MockKeyVentika...')

# Credenciales de Administrador (configúralas en tu .env; estas son solo un fallback de desarrollo)
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "ventika2026")


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def init_db():
    """Inicializa la base de datos SQLite para productos"""
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            price REAL NOT NULL,
            category TEXT NOT NULL,
            size TEXT NOT NULL,
            stock INTEGER NOT NULL,
            image_filename TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()


init_db()


def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn


# ----------------------------------------------------
# RUTAS PÚBLICAS (TIENDA VENTIKA)
# ----------------------------------------------------

@app.route('/')
def index():
    categoria = request.args.get('categoria')
    conn = get_db_connection()
    if categoria:
        products = conn.execute('SELECT * FROM products WHERE category = ?', (categoria,)).fetchall()
    else:
        products = conn.execute('SELECT * FROM products').fetchall()
    conn.close()
    return render_template('index.html', products=products, categoria_actual=categoria)


@app.route('/producto/<int:id>')
def detalle_producto(id):
    conn = get_db_connection()
    product = conn.execute('SELECT * FROM products WHERE id = ?', (id,)).fetchone()
    conn.close()
    if not product:
        flash("Producto no encontrado.", "error")
        return redirect(url_for('index'))
    return render_template('producto.html', product=product)


# ----------------------------------------------------
# CARRITO DE COMPRAS Y PAGOS (STRIPE)
# ----------------------------------------------------

@app.route('/carrito')
def ver_carrito():
    carrito = session.get('carrito', {})
    productos_en_carrito = []
    total = 0
    conn = get_db_connection()

    productos_invalidos = []
    for prod_id, cantidad in carrito.items():
        product = conn.execute('SELECT * FROM products WHERE id = ?', (int(prod_id),)).fetchone()
        if product:
            subtotal = product['price'] * cantidad
            total += subtotal
            productos_en_carrito.append({
                'product': product,
                'cantidad': cantidad,
                'subtotal': subtotal
            })
        else:
            # El producto fue eliminado del catálogo después de agregarse al carrito
            productos_invalidos.append(prod_id)
    conn.close()

    if productos_invalidos:
        for pid in productos_invalidos:
            carrito.pop(pid, None)
        session['carrito'] = carrito

    return render_template('carrito.html', items=productos_en_carrito, total=total)


@app.route('/agregar-carrito/<int:id>', methods=['POST'])
def agregar_carrito(id):
    cantidad = int(request.form.get('cantidad', 1))

    conn = get_db_connection()
    product = conn.execute('SELECT * FROM products WHERE id = ?', (id,)).fetchone()
    conn.close()

    if not product:
        flash("Ese producto ya no está disponible.", "error")
        return redirect(url_for('index'))

    carrito = session.get('carrito', {})
    str_id = str(id)
    cantidad_actual = carrito.get(str_id, 0)
    nueva_cantidad = cantidad_actual + cantidad

    if nueva_cantidad > product['stock']:
        flash(f"Solo quedan {product['stock']} unidades disponibles de '{product['title']}'.", "error")
        return redirect(url_for('detalle_producto', id=id))

    carrito[str_id] = nueva_cantidad
    session['carrito'] = carrito
    flash("Producto añadido al carrito.", "success")
    return redirect(url_for('ver_carrito'))


@app.route('/eliminar-carrito/<int:id>')
def eliminar_carrito(id):
    carrito = session.get('carrito', {})
    str_id = str(id)
    if str_id in carrito:
        del carrito[str_id]
        session['carrito'] = carrito
    return redirect(url_for('ver_carrito'))


@app.route('/crear-checkout-session', methods=['POST'])
def crear_checkout_session():
    carrito = session.get('carrito', {})
    if not carrito:
        return redirect(url_for('ver_carrito'))

    line_items = []
    conn = get_db_connection()

    for prod_id, cantidad in carrito.items():
        product = conn.execute('SELECT * FROM products WHERE id = ?', (int(prod_id),)).fetchone()
        if product:
            line_items.append({
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': product['title'],
                    },
                    'unit_amount': int(product['price'] * 100),  # En centavos
                },
                'quantity': cantidad,
            })
    conn.close()

    if not line_items:
        flash("Tu carrito no tiene productos válidos.", "error")
        return redirect(url_for('ver_carrito'))

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url=url_for('pago_exitoso', _external=True),
            cancel_url=url_for('ver_carrito', _external=True),
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        flash(f"Error procesando el pago con Stripe: {e}", "error")
        return redirect(url_for('ver_carrito'))


@app.route('/pago-exitoso')
def pago_exitoso():
    session.pop('carrito', None)
    return render_template('pago_exitoso.html')


# ----------------------------------------------------
# PANEL DE ADMINISTRADOR
# ----------------------------------------------------

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        user = request.form.get('username')
        password = request.form.get('password')
        if user == ADMIN_USER and password == ADMIN_PASS:
            session['admin_logged'] = True
            flash("Bienvenido al panel de administración, Eriel.", "success")
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Credenciales incorrectas.", "error")
    return render_template('admin_login.html')


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged', None)
    return redirect(url_for('admin_login'))


@app.route('/admin/dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if not session.get('admin_logged'):
        return redirect(url_for('admin_login'))

    conn = get_db_connection()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        price = float(request.form.get('price', 0))
        category = request.form.get('category')
        size = request.form.get('size')
        stock = int(request.form.get('stock', 0))

        # Generador automático de título/descripción si se dejan vacíos
        if not title:
            title = f"Exclusiva Prenda {category.capitalize()} VTK"
        if not description:
            description = ("Diseño de alta costura para la colección de lujo VENTIKA. "
                            "Confeccionado en materiales premium con detalles dorados.")

        file = request.files.get('image')
        image_filename = "default.jpg"
        if file and file.filename != '':
            if allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower()
                # Nombre único para evitar que dos productos se sobrescriban entre sí
                image_filename = f"{uuid.uuid4().hex}.{ext}"
                safe_name = secure_filename(image_filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], safe_name))
                image_filename = safe_name
            else:
                flash("Formato de imagen no permitido. Usa PNG, JPG, JPEG, WEBP o GIF.", "error")
                conn.close()
                return redirect(url_for('admin_dashboard'))

        conn.execute(
            'INSERT INTO products (title, description, price, category, size, stock, image_filename) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (title, description, price, category, size, stock, image_filename)
        )
        conn.commit()
        flash("Producto agregado con éxito a VENTIKA.", "success")
        return redirect(url_for('admin_dashboard'))

    products = conn.execute('SELECT * FROM products').fetchall()
    conn.close()
    return render_template('admin_dashboard.html', products=products)


@app.route('/admin/eliminar/<int:id>')
def admin_eliminar(id):
    if not session.get('admin_logged'):
        return redirect(url_for('admin_login'))
    conn = get_db_connection()
    conn.execute('DELETE FROM products WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash("Producto eliminado correctamente.", "success")
    return redirect(url_for('admin_dashboard'))


# ----------------------------------------------------
# INTEGRACIÓN SHOPIFY ADMIN API
# ----------------------------------------------------

@app.route('/admin/sincronizar-shopify', methods=['POST'])
def sincronizar_shopify():
    if not session.get('admin_logged'):
        return redirect(url_for('admin_login'))

    shop_url = request.form.get('shop_url')  # ej: tu-tienda.myshopify.com
    access_token = request.form.get('access_token')  # Admin API Access Token

    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json"
    }

    url = f"https://{shop_url}/admin/api/2024-01/products.json"

    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            shopify_data = response.json().get('products', [])
            conn = get_db_connection()
            count_imported = 0

            for sp in shopify_data:
                title = sp.get('title')
                body_html = sp.get('body_html') or 'Sin descripción'
                variants = sp.get('variants') or [{}]
                price = float(variants[0].get('price', 0.0))
                inventory = variants[0].get('inventory_quantity', 10)
                images = sp.get('images') or [{}]
                img_src = images[0].get('src', '') if images else ''

                conn.execute(
                    'INSERT INTO products (title, description, price, category, size, stock, image_filename) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (title, body_html, price, "Shopify", "Única", inventory, img_src if img_src else "default.jpg")
                )
                count_imported += 1
            conn.commit()
            conn.close()
            flash(f"¡Sincronización exitosa! Se importaron {count_imported} productos desde Shopify.", "success")
        else:
            flash(f"Error al conectar con Shopify. Código HTTP: {response.status_code}", "error")
    except Exception as e:
        flash(f"Error de conexión: {e}", "error")

    return redirect(url_for('admin_dashboard'))


if __name__ == '__main__':
    debug_mode = os.environ.get("FLASK_DEBUG", "true").lower() == "true"
    app.run(debug=debug_mode, port=5000)
