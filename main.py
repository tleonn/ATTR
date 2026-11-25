import argparse
import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))

import psycopg2

import attr
import cargar_infraestructura
import cargar_nodos_clave
import cargar_sismo
import comparar_attr
import prob_falla
import topologia
from db import ROOT, conectar, ejecutar_sql
from mapa import generar_mapa


def titulo(texto):
    print(f"\n{'=' * 70}\n{texto}\n{'=' * 70}")


def levantar_docker():
    titulo("0. Base de datos (docker compose)")
    subprocess.run(["docker", "compose", "up", "-d", "--wait"], cwd=ROOT, check=True)


def esperar_bd(intentos=30):
    for _ in range(intentos):
        try:
            conectar("postgres").close()
            return
        except psycopg2.OperationalError:
            time.sleep(2)
    raise SystemExit("No se pudo conectar a PostgreSQL")


def recrear_bd():
    nombre = os.getenv("DB_NAME", "attr")
    conn = conectar("postgres")
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(f'DROP DATABASE IF EXISTS "{nombre}" WITH (FORCE)')
        cur.execute(f'CREATE DATABASE "{nombre}"')
    conn.close()
    print(f"BD '{nombre}' creada vacía")


def cargar_main_sql():
    titulo("1. Carga de main.sql (infraestructura, topología, sismo)")
    conn = conectar()
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute((ROOT / "main.sql").read_text(encoding="utf-8"))
        cur.execute("SELECT (SELECT count(*) FROM red), (SELECT count(*) FROM red_vertices_pgr),"
                    " (SELECT count(*) FROM nodos_clave), (SELECT count(*) FROM sismo),"
                    " (SELECT sum(prob_falla) FROM red)")
        red, vert, nodos, sismo, suma_p = cur.fetchone()
    conn.close()
    print(f"red: {red} enlaces | red_vertices_pgr: {vert} | nodos_clave: {nodos} | sismo: {sismo}")
    return red, vert, suma_p


def recalcular_topologia():
    titulo("2. Topología sobre las capas cargadas (pgr_nodeNetwork + pgr_createTopology)")
    topologia.main()


def verificar_contra_main_sql(referencia):
    red0, vert0, suma0 = referencia
    conn = conectar()
    with conn.cursor() as cur:
        cur.execute("SELECT (SELECT count(*) FROM red), (SELECT count(*) FROM red_vertices_pgr),"
                    " (SELECT sum(prob_falla) FROM red)")
        red, vert, suma = cur.fetchone()
    conn.close()
    igual = red == red0 and vert == vert0 and abs(suma - suma0) < 1e-9
    print(f"\nComparación con main.sql: enlaces {red}/{red0}, vértices {vert}/{vert0}, "
          f"Σ prob_falla {suma:.6f}/{suma0:.6f} -> {'coinciden' if igual else 'NO coinciden'}")


def construir_desde_cero():
    titulo("1. Carga de shapefiles")
    cargar_infraestructura.main()
    titulo("2. Nodos clave")
    cargar_nodos_clave.main()
    titulo("3. Topología (pgr_nodeNetwork + pgr_createTopology)")
    topologia.main()
    titulo("4. Sismo 27F desde USGS")
    cargar_sismo.main()


def calcular_attr(conn, escenario, iteraciones):
    res = attr.calcular_attr(conn, iteraciones)
    attr.guardar(conn, escenario, res)
    attr.imprimir(escenario, res)


def main():
    parser = argparse.ArgumentParser(description="Tarea 2: ATTR de la Internet chilena ante el 27F")
    parser.add_argument("--desde-cero", action="store_true",
                        help="reconstruye todo desde los shapefiles en vez de cargar main.sql")
    parser.add_argument("--sin-docker", action="store_true",
                        help="usa una BD ya levantada (variables DB_* / .env)")
    parser.add_argument("--no-abrir", action="store_true", help="no abre el mapa en el navegador")
    parser.add_argument("--iteraciones", type=int, default=attr.ITERACIONES)
    args = parser.parse_args()

    if not args.sin_docker:
        levantar_docker()
    esperar_bd()
    recrear_bd()

    referencia = None
    if args.desde_cero:
        construir_desde_cero()
    else:
        referencia = cargar_main_sql()
        recalcular_topologia()

    conn = conectar()
    titulo("ATTR en operación (prob_falla = 0)")
    with conn.cursor() as cur:
        cur.execute("UPDATE red SET prob_falla = 0")
    conn.commit()
    calcular_attr(conn, "operacion", args.iteraciones)

    titulo("Probabilidades de falla por el terremoto 27F")
    conn.close()
    prob_falla.main()
    if referencia:
        verificar_contra_main_sql(referencia)
    conn = conectar()

    titulo("ATTR post terremoto 27F")
    calcular_attr(conn, "terremoto", args.iteraciones)

    titulo("Comparación")
    with conn.cursor() as cur:
        comparar_attr.comparar(cur)
        comparar_attr.nodos(cur)
        comparar_attr.criticos(cur)

    titulo("Mapa Leaflet")
    destino = generar_mapa(conn)
    conn.close()
    print(f"Mapa: {destino}")
    if not args.no_abrir:
        webbrowser.open(destino.as_uri())


if __name__ == "__main__":
    main()
