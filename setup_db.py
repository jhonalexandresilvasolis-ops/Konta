import sqlite3
import os
def crear_base_datos():
    # Conectamos (o creamos) el archivo de base de datos
    
    db_path = os.environ.get('DATABASE_PATH', 'contabilidad.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Tabla de CUENTAS
    # Guardará: Activos, Pasivos, etc.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cuentas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT NOT NULL UNIQUE,
            nombre TEXT NOT NULL,
            tipo TEXT NOT NULL
        )
    ''')

    # 2. Tabla de ASIENTOS (Cabecera)
    # Guardará: Fecha y descripción general de la operación
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS asientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            descripcion TEXT NOT NULL
        )
    ''')

    # 3. Tabla de MOVIMIENTOS (Detalle)
    # Guardará: Qué cuenta se movió, cuánto al Debe y cuánto al Haber
    # Está vinculada al Asiento (id_asiento) y a la Cuenta (id_cuenta)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movimientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_asiento INTEGER NOT NULL,
            id_cuenta INTEGER NOT NULL,
            debe REAL DEFAULT 0,
            haber REAL DEFAULT 0,
            FOREIGN KEY (id_asiento) REFERENCES asientos (id),
            FOREIGN KEY (id_cuenta) REFERENCES cuentas (id)
        )
    ''')

    print("Base de datos 'contabilidad.db' y tablas creadas con éxito.")
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    crear_base_datos()