# crear_superadmin.py
from app import create_app
from models import db, Usuario, Rol

app = create_app()

def crear_admin():
    with app.app_context():
        print("--- CREACIÓN DE SUPER ADMIN ---")
        email = input("Ingresa el email del admin: ")
        password = input("Ingresa la contraseña del admin: ")
        
        # Verificar si el rol Admin existe
        rol_admin = Rol.query.filter_by(nombre='Admin').first()
        if not rol_admin:
            print("Error: El rol 'Admin' no existe en la BD. Ejecuta el script SQL primero.")
            return

        # Verificar si el usuario ya existe
        if Usuario.query.filter_by(email=email).first():
            print("Error: Ese email ya está registrado.")
            return

        nuevo_admin = Usuario(
            nombre_completo="Super Administrador",
            email=email,
            rol_id=rol_admin.id,
            activo=True
        )
        nuevo_admin.set_password(password)
        
        db.session.add(nuevo_admin)
        db.session.commit()
        print(f"¡Éxito! Usuario {email} creado correctamente.")

if __name__ == '__main__':
    crear_admin()