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

### 2. Nodos clave

```bash
python scripts/cargar_nodos_clave.py
```

Carga `data/nodos_clave.csv` en la tabla `nodos_clave`, 17 nodos que **generan**
(aterrizajes de cables submarinos en Arica y Valparaíso, salida terrestre a Argentina por
Los Andes), **intercambian** (PITs y data centers de Santiago, anillos urbanos de Concepción y
Temuco) o **reciben** información (capitales regionales sobre la troncal). Criterio, fuentes
y ubicación en [`docs/nodos_clave.md`](docs/nodos_clave.md).

### 3. Topología

```bash
python scripts/topologia.py
```

Une las capas en EPSG:32719, corta las uniones en "T" con `pgr_nodeNetwork` y ejecuta
`pgr_createTopology('red', 10, 'geom', 'id')` (tolerancia de 10 m). El resultado es la tabla de
enlaces `red` (con `prob_falla = 0` por defecto) y la tabla de vértices `red_vertices_pgr`.
La fibra es la red real; la postación, los caminos, los ferrys, los accesos a nodos clave y un
puente de 2,6 km se marcan como **sintéticos**. Los 17 nodos clave quedan en la componente
principal (97,6 % de los vértices). Detalle, tolerancia y limitaciones en
[`docs/topologia.md`](docs/topologia.md).

### 4. ATTR en operación

```bash
python scripts/attr.py --escenario operacion
python tests/test_attr.py        # validación contra casos teóricos
```

ATTR = promedio, sobre los 136 pares de nodos clave, de la probabilidad de que queden
conectados. Se calcula de forma exacta cuando quedan pocos enlaces con 0 < p < 1, y por Monte
Carlo (20.000 iteraciones, cota de Hoeffding para un error de ±0,01 con 95 % de confianza) en
otro caso. **Con la infraestructura en operación, ATTR = 1,0000** (exacto): los 17 nodos
clave están conectados. Definición, referencias y método en [`docs/attr.md`](docs/attr.md).

### 5. Sismo 27F (USGS)

```bash
python scripts/cargar_sismo.py
```

Descarga el GeoJSON del sismo Mw 8.8 del 27-02-2010 desde la API FDSN de USGS (evento
`official20100227063411530_30`) y lo carga en la tabla `sismo`. Si no hay conexión, usar la
copia en `data/sismo_27F.geojson`. Epicentro: (−36,122; −72,898), profundidad 22,9 km.

### 6. Modelo de falla

```bash
python scripts/modelo_falla.py   # curva PGA y probabilidad de falla vs. distancia
```

Atenuación de PGA para subducción de **Youngs et al. (1997)** (SRL 68(1)), a partir de la
distancia al epicentro, más la fragilidad lognormal de **HAZUS** para circuitos de distribución
aéreos (Tabla 8-30). La probabilidad de falla de un enlace es la fracción esperada de circuitos
que fallan: ≈ 0,11 en el epicentro, 0,02 a 100 km y ≈ 0 sobre 300 km. Fórmulas, parámetros y
justificación en [`docs/sismo_modelo_falla.md`](docs/sismo_modelo_falla.md).

### 7. Probabilidad de falla por enlace

```bash
python scripts/prob_falla.py
```

`sql/02_prob_falla.sql` implementa el modelo como funciones SQL (`pga_youngs`, `fragilidad`,
`prob_falla_sismo`) y actualiza `red.prob_falla` usando `ST_Distance` entre cada enlace y el
epicentro. Resultado: p máx = 0,105 en la costa de Ñuble, cerca de
Cobquecura; 553 enlaces (~2.285 km) con p > 0,01 y 74 % de la red con p ≤ 0,0001. Enlaces
más y menos afectados en [`docs/prob_falla.md`](docs/prob_falla.md).

## Estructura

```
.
├── data/
│   ├── nodos_clave.csv
│   ├── sismo_27F.geojson
│   └── infraestructura/
│       ├── fibra_optica_detectada.*
│       ├── camino_sin_postacion_detectado.*
│       ├── postacion_electrica_detectada.*
│       └── trayecto_en_ferry.*
├── docs/
│   ├── attr.md
│   ├── nodos_clave.md
│   ├── prob_falla.md
│   ├── sismo_modelo_falla.md
│   └── topologia.md
├── scripts/
│   ├── db.py                       # conexión a la BD
│   ├── cargar_infraestructura.py   # shapefiles -> PostGIS
│   ├── cargar_nodos_clave.py       # nodos clave -> PostGIS
│   ├── topologia.py                # pgr_nodeNetwork + pgr_createTopology
│   ├── attr.py                     # ATTR exacto / Monte Carlo
│   ├── cargar_sismo.py             # GeoJSON USGS -> tabla sismo
│   ├── modelo_falla.py             # Youngs (1997) + fragilidad HAZUS
│   └── prob_falla.py               # probabilidad de falla por enlace
├── sql/
│   ├── 00_extensiones.sql
│   ├── 01_topologia.sql
│   └── 02_prob_falla.sql
├── tests/
│   └── test_attr.py
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
| `scipy`           | Componentes conexas (`csgraph`) en el cálculo del ATTR |
