"""Carga los nodos clave (data/nodos_clave.csv) en la tabla nodos_clave.

Además reporta la distancia de cada nodo al tramo de infraestructura más
cercano (en cualquiera de las 4 capas), lo que permite verificar que todos
pueden ubicarse sobre la topología.
"""
import csv

from psycopg2.extras import execute_values

from db import DATA_DIR, conectar

CAPAS = ["fibra_optica", "camino_sin_postacion", "postacion_electrica", "trayecto_ferry"]


def cargar(conn):
    with open(DATA_DIR / "nodos_clave.csv", encoding="utf-8") as f:
        filas = [
            (int(r["id"]), r["nombre"], r["tipo"], r["rol"], r["justificacion"],
             r["fuente"], float(r["lon"]), float(r["lat"]))
            for r in csv.DictReader(f)
        ]
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS nodos_clave CASCADE")
        cur.execute(
            """CREATE TABLE nodos_clave (
                   id            integer PRIMARY KEY,
                   nombre        text NOT NULL,
                   tipo          text,
                   rol           text,      -- genera / intercambia / recibe
                   justificacion text,
                   fuente        text,
                   geom          geometry(Point, 4326)
               )"""
        )
        execute_values(
            cur,
            "INSERT INTO nodos_clave VALUES %s",
            filas,
            template="(%s,%s,%s,%s,%s,%s, ST_SetSRID(ST_MakePoint(%s,%s),4326))",
        )
    conn.commit()
    return len(filas)


def distancia_a_infraestructura(conn):
    union = " UNION ALL ".join(f"SELECT '{c}' AS capa, geom FROM {c}" for c in CAPAS)
    sql = f"""
        SELECT n.id, n.nombre, n.rol, cerca.capa,
               round((ST_Distance(n.geom::geography, cerca.geom::geography)/1000)::numeric, 2)
        FROM nodos_clave n
        CROSS JOIN LATERAL (
            SELECT capa, geom FROM ({union}) l
            ORDER BY l.geom <-> n.geom LIMIT 1
        ) cerca
        ORDER BY n.id
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchall()


def main():
    conn = conectar()
    n = cargar(conn)
    print(f"{n} nodos clave cargados\n")
    print(f"{'id':>3}  {'Nodo':<14}{'Rol':<20}{'Capa más cercana':<22}{'Dist (km)':>9}")
    for id_, nombre, rol, capa, km in distancia_a_infraestructura(conn):
        print(f"{id_:>3}  {nombre:<14}{rol:<20}{capa:<22}{km:>9}")
    conn.close()


if __name__ == "__main__":
    main()
