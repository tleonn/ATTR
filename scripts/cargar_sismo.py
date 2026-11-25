import json

import requests
from psycopg2.extras import Json

from db import DATA_DIR, conectar

EVENTO = "official20100227063411530_30"
URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
ARCHIVO = DATA_DIR / "sismo_27F.geojson"


def descargar():
    """Busca el sismo M8.8 del 27-02-2010 en la API FDSN de USGS; si no hay red usa la copia local."""
    try:
        r = requests.get(URL, timeout=30, params={
            "format": "geojson", "starttime": "2010-02-27", "endtime": "2010-02-28",
            "minmagnitude": 8.5,
        })
        r.raise_for_status()
        datos = r.json()
        if not ARCHIVO.exists():
            ARCHIVO.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Descargado desde USGS: {r.url}")
    except requests.RequestException as e:
        print(f"Sin acceso a USGS ({e.__class__.__name__}); se usa {ARCHIVO.name}")
        datos = json.loads(ARCHIVO.read_text(encoding="utf-8"))
    return next(f for f in datos["features"] if f["id"] == EVENTO)


def cargar(conn, evento):
    lon, lat, prof = evento["geometry"]["coordinates"]
    p = evento["properties"]
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS sismo CASCADE")
        cur.execute(
            """CREATE TABLE sismo (
                   id             text PRIMARY KEY,
                   lugar          text,
                   magnitud       double precision,
                   tipo_magnitud  text,
                   fecha_utc      timestamptz,
                   profundidad_km double precision,
                   url            text,
                   geojson        jsonb,
                   geom           geometry(Point, 4326)
               )"""
        )
        cur.execute(
            """INSERT INTO sismo VALUES (%s,%s,%s,%s, to_timestamp(%s / 1000.0), %s,%s,%s,
                                         ST_SetSRID(ST_MakePoint(%s,%s), 4326))""",
            (evento["id"], p["place"], p["mag"], p.get("magType"), p["time"], prof,
             p["url"], Json(evento), lon, lat),
        )
    conn.commit()


def main():
    conn = conectar()
    cargar(conn, descargar())
    with conn.cursor() as cur:
        cur.execute(
            """SELECT id, lugar, magnitud, tipo_magnitud, fecha_utc AT TIME ZONE 'UTC',
                      profundidad_km, ST_Y(geom), ST_X(geom) FROM sismo"""
        )
        id_, lugar, mag, tipo, fecha, prof, lat, lon = cur.fetchone()
    print(f"\nTabla sismo:\n  id: {id_}\n  lugar: {lugar}\n  magnitud: {mag} {tipo}"
          f"\n  fecha (UTC): {fecha}\n  epicentro: {lat}, {lon}\n  profundidad: {prof} km")
    conn.close()


if __name__ == "__main__":
    main()
