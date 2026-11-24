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

## Estructura

```
.
├── data/
│   └── infraestructura/
│       ├── fibra_optica_detectada.*
│       ├── camino_sin_postacion_detectado.*
│       ├── postacion_electrica_detectada.*
│       └── trayecto_en_ferry.*
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
