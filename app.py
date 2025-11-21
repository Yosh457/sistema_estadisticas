import os
from dotenv import load_dotenv
from flask import Flask, redirect, url_for
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

    # --- REGISTRO DE BLUEPRINTS ---
    from blueprints.auth import auth_bp 
    app.register_blueprint(auth_bp)

    from blueprints.admin import admin_bp
    app.register_blueprint(admin_bp)

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