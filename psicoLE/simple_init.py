#!/usr/bin/env python3
import os
import sqlite3
from werkzeug.security import generate_password_hash

# Asegurarse de que el directorio instance existe
os.makedirs('instance', exist_ok=True)

# Ruta a la base de datos
db_path = 'instance/psicole.db'

# Eliminar la base de datos si existe
if os.path.exists(db_path):
    os.remove(db_path)

# Conectar a la base de datos (se crea automáticamente si no existe)
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Crear la tabla de roles
cursor.execute('''
    CREATE TABLE roles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        description TEXT
    )
''')

# Crear la tabla de usuarios
cursor.execute('''
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        is_active BOOLEAN DEFAULT 1,
        role_id INTEGER,
        FOREIGN KEY (role_id) REFERENCES roles (id)
    )
''')

# Insertar el rol de administrador
cursor.execute(
    "INSERT INTO roles (name, description) VALUES (?, ?)",
    ('admin', 'Administrator with full access')
)

# Obtener el ID del rol de administrador
admin_role_id = cursor.lastrowid

# Crear el usuario administrador
username = "admin"
email = "admin@example.com"
password = "admin123"
password_hash = generate_password_hash(password, method='pbkdf2:sha256')

cursor.execute(
    "INSERT INTO users (username, email, password_hash, is_active, role_id) VALUES (?, ?, ?, ?, ?)",
    (username, email, password_hash, 1, admin_role_id)
)

# Guardar los cambios
conn.commit()

# Cerrar la conexión
conn.close()

print("\n¡Base de datos inicializada correctamente!")
print("======================================")
print(f"Usuario: {username}")
print(f"Correo electrónico: {email}")
print(f"Contraseña: {password}")
print("\n¡IMPORTANTE! Por favor, cambia esta contraseña después de iniciar sesión.")
print("======================================\n")
