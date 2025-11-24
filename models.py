from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import pytz

db = SQLAlchemy()

def obtener_hora_chile():
    chile_tz = pytz.timezone('America/Santiago')
    return datetime.now(chile_tz).replace(tzinfo=None)

class Rol(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    usuarios = db.relationship('Usuario', back_populates='rol')

class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    nombre_completo = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=obtener_hora_chile)
    
    # Gestión de contraseñas
    cambio_clave_requerido = db.Column(db.Boolean, default=False, nullable=False)
    reset_token = db.Column(db.String(32), nullable=True)
    reset_token_expiracion = db.Column(db.DateTime, nullable=True)

    # Relación con Rol
    rol_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    rol = db.relationship('Rol', back_populates='usuarios')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Log(db.Model):
    __tablename__ = 'logs'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=obtener_hora_chile) 
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    usuario_nombre = db.Column(db.String(255))
    accion = db.Column(db.String(255), nullable=False)
    detalles = db.Column(db.Text)
    
    usuario = db.relationship('Usuario', backref=db.backref('logs', lazy=True))

# --- MODELOS ESTADÍSTICAS ---

class Grupo(db.Model):
    __tablename__ = 'grupos'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    imagen = db.Column(db.String(255)) 
    orden = db.Column(db.Integer, default=0)
    
    # Relación para acceder a los dashboards de este grupo
    dashboards = db.relationship('Dashboard', back_populates='grupo')

class Dashboard(db.Model):
    __tablename__ = 'dashboards'
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(255), nullable=False)
    descripcion = db.Column(db.Text)
    url_iframe = db.Column(db.Text, nullable=False) # Aquí va el link de Power BI
    imagen_preview = db.Column(db.String(255)) # Nombre del archivo en static (ej: dashboard1.png)
    activo = db.Column(db.Boolean, default=True)
    orden = db.Column(db.Integer, default=0) # Para controlar cuál sale primero

    # Llave foránea para saber a qué grupo pertenece
    grupo_id = db.Column(db.Integer, db.ForeignKey('grupos.id'), nullable=True)
    grupo = db.relationship('Grupo', back_populates='dashboards')