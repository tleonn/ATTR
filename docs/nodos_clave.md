# Nodos clave de la infraestructura

## Criterio

Un **nodo clave** es un punto de la red donde la información se **genera** (entra o sale del
país, o se produce en data centers), se **intercambia** (puntos de intercambio de tráfico y
anillos urbanos donde se interconectan los operadores) o se **recibe** (centros de población
servidos por la red troncal). El criterio se basa en lo que reporta el *Estudio y
Recomendaciones sobre la Resiliencia de la infraestructura de la Internet chilena* (NIC Chile
Research Labs, proyecto CORFO 15BPE-47225, en adelante "Estudio"):

1. **Conexión internacional** (Estudio, p. 22, respuesta oficial de SUBTEL): *"Chile cuenta con
   grandes redes de transporte de fibra óptica desde Arica hasta Puerto Montt [...] y se
   conectan al backbone internacional de Internet mediante cables submarinos, hacia el norte
   por el Océano Pacífico y desde Santiago hacia Argentina"*. Esto determina los nodos que
   **generan/reciben** tráfico internacional: los aterrizajes de cables submarinos (capa
   `mapa_cables_submarinos_nodos` del Estudio, p. 27, fuente TeleGeography) y el punto
   limítrofe terrestre hacia Argentina (el Estudio modela 8 puntos limítrofes, p. 39 y p. 46).
2. **Intercambio** (Estudio, p. 22): *"en las principales ciudades del país (Santiago,
   Valparaíso, Temuco y Concepción) existen anillos de fibra urbana"*. Además, el Estudio
   recomienda estudiar los **PITs y data centers** (p. 75), que en Chile se concentran en
   Santiago (PIT Chile, NAP Chile de la Cámara de Comercio de Santiago).
3. **Recepción / nodos troncales** (Estudio, p. 39): el grafo del Estudio usa las comunas como
   nodos (346 comunas + 8 puntos limítrofes). Para que el ATTR sea manejable
   (17·16/2 = 136 pares) se toman las **16 capitales regionales**, que cubren la troncal de
   norte a sur, más el punto limítrofe de Los Andes.

## Lista de nodos clave

| id | Nodo         | Rol                 | Tipo                                         | Lat      | Lon      |
|---:|--------------|---------------------|----------------------------------------------|---------:|---------:|
|  1 | Arica        | genera / recibe     | Aterrizaje SAm-1 + capital regional          | -18.4783 | -70.3126 |
|  2 | Iquique      | recibe              | Nodo troncal (capital regional)              | -20.2133 | -70.1503 |
|  3 | Antofagasta  | recibe              | Nodo troncal (capital regional)              | -23.6509 | -70.3975 |
|  4 | Copiapó      | recibe              | Nodo troncal (capital regional)              | -27.3668 | -70.3314 |
|  5 | La Serena    | recibe              | Nodo troncal (capital regional)              | -29.9045 | -71.2489 |
|  6 | Valparaíso   | genera / recibe     | Aterrizaje SAm-1 y Curie + anillo urbano     | -33.0472 | -71.6127 |
|  7 | Santiago     | intercambia / genera| PIT/IXP + data centers + anillo urbano       | -33.4378 | -70.6505 |
|  8 | Los Andes    | genera / recibe     | Punto limítrofe (Cristo Redentor → Argentina) | -32.8337 | -70.5983 |
|  9 | Rancagua     | recibe              | Nodo troncal (capital regional)              | -34.1708 | -70.7444 |
| 10 | Talca        | recibe              | Nodo troncal (capital regional)              | -35.4264 | -71.6554 |
| 11 | Chillán      | recibe              | Nodo troncal (capital regional)              | -36.6066 | -72.1034 |
| 12 | Concepción   | intercambia / recibe| Nodo troncal + anillo urbano                 | -36.8270 | -73.0498 |
| 13 | Temuco       | intercambia / recibe| Nodo troncal + anillo urbano                 | -38.7359 | -72.5904 |
| 14 | Valdivia     | recibe              | Nodo troncal (capital regional)              | -39.8142 | -73.2459 |
| 15 | Puerto Montt | recibe              | Extremo sur de la troncal Arica–Puerto Montt | -41.4693 | -72.9424 |
| 16 | Coyhaique    | recibe              | Nodo troncal (capital regional, zona austral) | -45.5712 | -72.0685 |
| 17 | Punta Arenas | recibe              | Nodo troncal (capital regional, zona austral) | -53.1638 | -70.9171 |

Las coordenadas corresponden al centro de cada ciudad; la justificación y la fuente de cada
nodo están en `data/nodos_clave.csv` y se cargan en la tabla `nodos_clave` de la BD.

## Ubicación en la infraestructura

`scripts/cargar_nodos_clave.py` mide la distancia de cada nodo al tramo más cercano:

| Nodo | Capa más cercana | Distancia (km) |
|------|------------------|---------------:|
| Arica | fibra_optica | 0,29 |
| Iquique | fibra_optica | 0,02 |
| Antofagasta | fibra_optica | 0,10 |
| Copiapó | fibra_optica | 0,01 |
| La Serena | fibra_optica | 0,04 |
| Valparaíso | fibra_optica | 0,26 |
| **Santiago** | fibra_optica | **9,21** |
| Los Andes | fibra_optica | 0,01 |
| Rancagua | fibra_optica | 0,35 |
| Talca | fibra_optica | 0,03 |
| Chillán | fibra_optica | 0,01 |
| Concepción | fibra_optica | 0,03 |
| Temuco | fibra_optica | 0,32 |
| Valdivia | fibra_optica | 0,00 |
| Puerto Montt | fibra_optica | 0,25 |
| Coyhaique | fibra_optica | 0,00 |
| Punta Arenas | fibra_optica | 0,48 |

16 de los 17 nodos están a menos de 0,5 km de un tendido de fibra. **Santiago queda a 9,2 km**
porque el levantamiento en terreno del Estudio recorrió caminos interurbanos y no el núcleo
urbano de Santiago (cuyos anillos de fibra SUBTEL reconoce, pero que no vienen en los datos).
### Ubicación en la topología

`scripts/topologia.py` une cada nodo clave que está a más de 10 m de un vértice con un enlace
**sintético** de acceso (`capa = 'acceso'`) y guarda en `nodos_clave.vertice` el vértice de
`red_vertices_pgr` que lo representa:

| id | Nodo | Vértice | Enlace de acceso (m) |
|---:|------|--------:|---------------------:|
|  1 | Arica        | 3431 |   983 |
|  2 | Iquique      | 3614 |   235 |
|  3 | Antofagasta  | 3393 |   501 |
|  4 | Copiapó      | 3491 |    86 |
|  5 | La Serena    | 2477 |   358 |
|  6 | Valparaíso   | 1991 | 1.763 |
|  7 | Santiago     | 3267 | **9.208** |
|  8 | Los Andes    | 3303 |    12 |
|  9 | Rancagua     | 3171 |   351 |
| 10 | Talca        | 2059 |   968 |
| 11 | Chillán      | 1492 |    13 |
| 12 | Concepción   |  385 |    46 |
| 13 | Temuco       |  981 |   457 |
| 14 | Valdivia     |  358 | — (sobre un vértice) |
| 15 | Puerto Montt |  754 |   364 |
| 16 | Coyhaique    | 2096 | — (sobre un vértice) |
| 17 | Punta Arenas | 3540 |   614 |

El enlace de Santiago (9,2 km) representa el anillo urbano que no viene en los datos. Los
17 nodos quedan en la componente principal de la topología (ver `topologia.md`).

## Limitaciones

- Los datos son de 2019 (levantamiento del Estudio); para el escenario del 27F (2010) el cable
  Curie (2019) no existía, pero Valparaíso ya era aterrizaje de SAm-1, así que su rol no
  cambia.
- Los data centers y PITs se agregan en un único nodo "Santiago" porque comparten vértice en la
  topología: separarlos solo agregaría pares trivialmente conectados al ATTR.
