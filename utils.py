# utils.py
from flask_login import current_user
from models import db, Log

def registrar_log(accion, detalles):
    """
    Registra una acción en la base de datos de logs.
    """
    if current_user.is_authenticated:
        try:
            nuevo_log = Log(
                usuario_id=current_user.id,
                usuario_nombre=current_user.nombre_completo,
                accion=accion,
                detalles=detalles
            )
            db.session.add(nuevo_log)
            db.session.commit()
        except Exception as e:
            # Si falla el log, no queremos que se caiga toda la app, 
            # pero imprimimos el error en consola.
            print(f"Error al registrar log: {e}")
            db.session.rollback()