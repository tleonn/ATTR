"""Conexión a la base de datos PostGIS/pgRouting levantada con docker compose."""
import os
from pathlib import Path

import psycopg2

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

ROOT = Path(__file__).resolve().parent.parent
SQL_DIR = ROOT / "sql"
DATA_DIR = ROOT / "data"


def conectar(dbname=None):
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5433"),
        dbname=dbname or os.getenv("DB_NAME", "attr"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
    )


def ejecutar_sql(conn, archivo):
    """Ejecuta un archivo .sql completo dentro de la conexión dada."""
    ruta = Path(archivo)
    if not ruta.is_absolute():
        ruta = SQL_DIR / ruta
    with conn.cursor() as cur:
        cur.execute(ruta.read_text(encoding="utf-8"))
    conn.commit()
