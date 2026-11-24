# ATTR — Resiliencia de la infraestructura de Internet chilena ante el terremoto 8.8 (27F)

Tarea 2 — CIT3435 Algoritmos de Ruteo y Redes Resilientes.

Se calcula el **ATTR** (*Average Two-Terminal Reliability*: confiabilidad promedio entre pares de nodos clave)
de la infraestructura de fibra óptica reportada en el *Estudio y Recomendaciones sobre la
Resiliencia de la infraestructura de la Internet chilena*, antes y después del terremoto
Mw 8.8 del 27-02-2010.

## Requisitos

- Docker + Docker Compose (base de datos PostgreSQL 17 + PostGIS 3.5 + pgRouting 3.7.3)
- Python 3.10+

## Puesta en marcha

```bash
# 1. Levantar la base de datos
docker compose up -d

# 2. Entorno Python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

La BD queda expuesta en `localhost:5433` (usuario/clave `postgres`/`postgres`, base `attr`).
Para cambiar estos valores, copiar `.env.example` a `.env`.

## Etapas

### 1. Carga de la infraestructura

```bash
python scripts/cargar_infraestructura.py
```

Crea las extensiones `postgis` y `pgrouting` y carga cada shapefile (EPSG:4326) en su tabla:

| Tabla                  | Tramos | Longitud (km) |
|------------------------|-------:|--------------:|
| `fibra_optica`         |  1.915 |        10.313 |
| `camino_sin_postacion` |  1.165 |         8.108 |
| `postacion_electrica`  |  1.213 |         6.712 |
| `trayecto_ferry`       |    204 |         2.390 |
| **Total**              |  4.497 |    **27.523** |

La fibra detectada (~10.300 km) es solo una parte del trazado; al sumar caminos sin postación, postación eléctrica y trayectos en ferry se llega a ~27.500 km, cerca de los ~28.000 km reportados en el Estudio.

## Estructura

```
.
├── data/
│   └── infraestructura/
│       ├── fibra_optica_detectada.*
│       ├── camino_sin_postacion_detectado.*
│       ├── postacion_electrica_detectada.*
│       └── trayecto_en_ferry.*
├── scripts/
│   ├── db.py                       # conexión a la BD
│   └── cargar_infraestructura.py   # shapefiles -> PostGIS
├── sql/
│   └── 00_extensiones.sql
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Dependencias

| Librería          | Uso                                                   |
|-------------------|-------------------------------------------------------|
| `psycopg2-binary` | Conexión a PostgreSQL/PostGIS                         |
| `folium`          | Generación del mapa Leaflet                           |
| `requests`        | Descarga del GeoJSON del sismo desde USGS             |
| `numpy`           | Simulación Monte Carlo del ATTR                       |
| `python-dotenv`   | Lectura opcional de credenciales desde `.env`         |
| `pyshp`           | Lectura de shapefiles (la imagen no trae `shp2pgsql`) |
