# VENTIKA — Guía rápida

## Instalación local
1. Instala Python 3.10+ (marca "Add Python to PATH" en la instalación).
2. Abre una terminal dentro de esta carpeta.
3. (Opcional pero recomendado) Crea un entorno virtual:
   - Windows: `python -m venv venv` y luego `venv\Scripts\activate`
   - Mac/Linux: `python3 -m venv venv` y luego `source venv/bin/activate`
4. Instala las dependencias: `pip install -r requirements.txt`
5. Copia `.env.example` a `.env` y cambia los valores (usuario/contraseña de admin, llave secreta, llave de Stripe).
6. Ejecuta: `python app.py`
7. Abre `http://127.0.0.1:5000` para la tienda, y `http://127.0.0.1:5000/admin/login` para el panel de administrador (usa el usuario/contraseña que pusiste en tu `.env`).

## Cambios importantes respecto al código original
- Las contraseñas de admin y las llaves ya NO están escritas directamente en el código: se leen desde `.env` (más seguro).
- Los nombres de las imágenes subidas ahora son únicos automáticamente, para que dos productos nunca se sobrescriban entre sí.
- Se valida el stock disponible antes de dejar agregar productos al carrito.
- Si un producto se elimina del catálogo mientras estaba en el carrito de alguien, ya no rompe la página del carrito.

## Despliegue gratuito en Render
1. Sube esta carpeta a un repositorio de GitHub (asegúrate de que `.env` NO se suba, ya está en `.gitignore`).
2. Crea una cuenta gratuita en https://render.com
3. New + > Web Service > conecta tu repositorio.
4. Build Command: `pip install -r requirements.txt`
5. Start Command: `gunicorn app:app`
6. En la sección "Environment", agrega las mismas variables que tienes en tu `.env` (SECRET_KEY, ADMIN_USER, ADMIN_PASS, STRIPE_SECRET_KEY).
7. Render te dará una URL pública gratuita.

## Conectar Shopify
Desde el panel de Admin > "Sincronizar con Shopify Admin API", necesitas:
- La URL de tu tienda: `tu-tienda.myshopify.com`
- Un Admin API Access Token (se genera en Shopify: Configuración > Apps y canales de venta > Desarrollar apps > Crear app > permisos `read_products` y `read_inventory` > Instalar app > copiar el token que empieza con `shpat_`)
