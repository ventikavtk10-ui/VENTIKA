@echo off
cd /d "%~dp0"
echo ================================
echo   Instalando VENTIKA...
echo ================================
echo.

if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo Se creo tu archivo .env con valores de ejemplo.
    echo Puedes editarlo despues para cambiar tu usuario/contraseña de admin.
    echo.
)

pip install -r requirements.txt

echo.
echo ================================
echo   Encendiendo VENTIKA...
echo   Abre tu navegador en: http://127.0.0.1:5000
echo   Panel admin: http://127.0.0.1:5000/admin/login
echo   (usuario: admin | contraseña: ventika2026, a menos que las hayas cambiado en .env)
echo ================================
echo.

python app.py

pause
