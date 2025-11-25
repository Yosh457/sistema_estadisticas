import os
from dotenv import load_dotenv
from flask import Flask, redirect, url_for, flash
from flask_wtf.csrf import CSRFError
from models import db, Usuario
from extensions import login_manager, csrf

def create_app():
    app = Flask(__name__)
    app.jinja_env.add_extension('jinja2.ext.do')
    load_dotenv()

    # Configuración
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    db_pass = os.getenv('MYSQL_PASSWORD')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://root:{db_pass}@localhost/estadisticas_db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Inicialización
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    
    login_manager.login_view = 'auth.login'
    # Mensajes personalizados para el login_required (opcional, pero recomendado)
    login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'
    login_manager.login_message_category = 'warning'

    # --- MANEJO DE ERRORES CSRF (Token Vencido) ---
    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        flash('Tu sesión ha expirado o la solicitud no es válida. Por favor, ingresa nuevamente.', 'warning')
        return redirect(url_for('auth.login'))

    # --- SEGURIDAD: NO CACHE (Evitar botón 'Atrás' después de logout) ---
    @app.after_request
    def add_header(response):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response

    # --- REGISTRO DE BLUEPRINTS ---
    from blueprints.auth import auth_bp 
    app.register_blueprint(auth_bp)

    from blueprints.admin import admin_bp
    app.register_blueprint(admin_bp)

    from blueprints.estadisticas import estadisticas_bp
    app.register_blueprint(estadisticas_bp)

    # --- RUTAS GLOBALES ---
    @app.route('/')
    def index():
        return redirect(url_for('auth.login')) # Redirigimos al login

    return app

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)