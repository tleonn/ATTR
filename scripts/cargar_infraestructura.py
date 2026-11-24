"""Carga los shapefiles del Estudio (Respuesta T5610) en PostGIS.

Cada shapefile queda en su propia tabla con geometría LINESTRING en EPSG:4326
(el .prj de los archivos es GCS_WGS_1984). Se usa pyshp para no depender de
shp2pgsql/ogr2ogr, que no vienen en la imagen de pgRouting.
"""
import shapefile
from psycopg2.extras import execute_values

from db import DATA_DIR, conectar, ejecutar_sql

# tabla destino -> (shapefile, tipo de infraestructura según el Estudio)
CAPAS = {
    "fibra_optica": ("fibra_optica_detectada", "fibra óptica detectada"),
    "camino_sin_postacion": ("camino_sin_postacion_detectado", "camino sin postación"),
    "postacion_electrica": ("postacion_electrica_detectada", "postación eléctrica"),
    "trayecto_ferry": ("trayecto_en_ferry", "trayecto en ferry"),
}


def linea_wkt(puntos):
    return "LINESTRING(" + ",".join(f"{x} {y}" for x, y in puntos) + ")"


def cargar_capa(conn, tabla, archivo):
    lector = shapefile.Reader(str(DATA_DIR / "infraestructura" / archivo))
    filas = [
        (str(reg["id"]), linea_wkt(forma.points))
        for forma, reg in zip(lector.shapes(), lector.records())
    ]
    with conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS {tabla} CASCADE")
        cur.execute(
            f"""CREATE TABLE {tabla} (
                    gid      serial PRIMARY KEY,
                    id_orig  text,
                    geom     geometry(LineString, 4326)
                )"""
        )
        execute_values(
            cur,
            f"INSERT INTO {tabla} (id_orig, geom) VALUES %s",
            filas,
            template="(%s, ST_GeomFromText(%s, 4326))",
        )
        cur.execute(f"CREATE INDEX ON {tabla} USING gist (geom)")
    conn.commit()
    return len(filas)


def resumen(conn):
    """Cantidad de tramos y longitud (km, sobre el elipsoide) por capa."""
    consultas = [
        f"SELECT '{t}', count(*), round(sum(ST_Length(geom::geography))/1000) FROM {t}"
        for t in CAPAS
    ]
    with conn.cursor() as cur:
        cur.execute(" UNION ALL ".join(consultas))
        return cur.fetchall()


def main():
    conn = conectar()
    ejecutar_sql(conn, "00_extensiones.sql")
    for tabla, (archivo, _) in CAPAS.items():
        cargar_capa(conn, tabla, archivo)

    print(f"{'Capa':<22}{'Tramos':>8}{'Longitud (km)':>16}")
    total = 0
    for capa, n, km in resumen(conn):
        total += km
        print(f"{capa:<22}{n:>8}{km:>16,.0f}")
    print(f"{'TOTAL':<22}{'':>8}{total:>16,.0f}")
    conn.close()


if __name__ == "__main__":
    main()
