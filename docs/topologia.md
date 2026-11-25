# Topología de red (`pgr_createTopology`)

```bash
python scripts/topologia.py
```

## Procedimiento

1. **Unión de capas** (`sql/01_topologia.sql`): las 4 tablas cargadas en la etapa 1 se unen en
   `red_base`, reproyectadas a **EPSG:32719 (WGS84 / UTM 19S)** para que la tolerancia quede en
   metros.
2. **Nodado con `pgr_nodeNetwork`**: `pgr_createTopology` solo une *extremos* de tramos. En los
   datos hay uniones en "T" (un tramo que termina en el interior de otro; 70 solo entre tramos de
   fibra), que sin este paso quedarían desconectadas. `pgr_nodeNetwork` cortó 748 tramos y generó
   1.558 segmentos nuevos (4.497 → 5.307 tramos).
3. **Tabla `red`**: un enlace por segmento, con `capa`, `sintetico`, `largo_m`, `cost`,
   `reverse_cost` (largo geodésico en metros, red no dirigida) y **`prob_falla` = 0 por defecto**
   (infraestructura en operación).
4. **Enlaces de acceso** (sintéticos): cada nodo clave a más de 10 m de un vértice se une con un
   tramo recto al vértice más cercano (15 enlaces, 16 km; el más largo es Santiago, 9,2 km).
5. **`pgr_createTopology('red', 10, 'geom', 'id')`** → crea `source`/`target` y la tabla de
   vértices `red_vertices_pgr`.
6. **Enlaces puente** (sintéticos): mientras los nodos clave queden en más de una componente
   conexa, se une el par de vértices más cercano entre componentes y se recalcula la topología.
7. **Numeración reproducible**: `pgr_createTopology` numera los vértices según el orden en
   que procesa las filas, que puede variar entre ejecuciones. Después de cada llamada, los
   vértices se renumeran de oeste a este (por coordenada X y luego Y) y se actualizan `source`
   y `target`. Además, `red` se crea con un orden explícito (`ORDER BY` tramo original y
   sub-tramo), así que los ids de enlaces, vértices y nodos clave son los mismos en cada
   ejecución, tanto desde cero como desde `main.sql`.

### Salida de `pgr_createTopology`

```
pgr_createTopology('red', 10, 'geom', 'id', 'source', 'target', rows_where := 'true', clean := t)
Performing checks, please wait .....
Creating Topology, Please wait...
-------------> TOPOLOGY CREATED FOR  5322 edges
Rows with NULL geometry or NULL id: 0
Vertices table for table public.red is: public.red_vertices_pgr
```

## Tolerancia: 10 m

Distancia de cada extremo de un tramo de fibra al extremo de fibra más cercano:

| Distancia            | Extremos |
|----------------------|---------:|
| < 1 cm (coinciden)   |    3.375 |
| 1 – 6 m              |       16 |
| 23 – 87 m            |        7 |
| 109 m – 7 km         |      232 |
| sin vecino a < 2 km   |      200 |

El 99 % de los extremos coincide exactamente. Los desfases de 1 a 6 m son errores de
digitalización del levantamiento manual, y no hay casos entre 6 y 23 m. Por eso **10 m** une los
desfases sin fusionar tramos que de verdad están separados (> 23 m). Una tolerancia mayor
(p. ej. 100 m) crearía conexiones que no existen en el terreno.

## Resultado

| Capa        | Sintético | Enlaces |     km | Justificación |
|-------------|:---------:|--------:|-------:|---------------|
| `fibra`     | no        |   2.251 | 10.313 | Fibra detectada en terreno (archivo SAIP) |
| `postacion` | **sí**    |   1.422 |  6.712 | Camino con postación eléctrica: el Estudio lo documenta como ruta donde la fibra puede tenderse (p. 23) |
| `camino`    | **sí**    |   1.407 |  8.108 | Camino recorrido sin postación; lo usa el Estudio en su grafo (p. 39) |
| `ferry`     | **sí**    |     227 |  2.390 | Trayecto náutico; única vía física hacia parte de la zona austral |
| `acceso`    | **sí**    |      15 |     16 | Tramo recto nodo clave → vértice más cercano |
| `puente`    | **sí**    |       1 |      3 | 2,6 km en la desembocadura del río Maipo (San Antonio) que une el bloque norte-centro con el sur |

- **Vértices** (`red_vertices_pgr`): 4.583. **Enlaces** (`red`): 5.323, todos con `prob_falla = 0`.
- **Componentes conexas**: 20. La principal tiene 4.471 vértices (97,6 %) y 27.109 km (98 %), y
  contiene a **los 17 nodos clave**. Las otras 19 son fragmentos de 2 a 16 vértices (≤ 69 km),
  entre ellos Isla de Pascua, que no afectan el ATTR porque no tienen nodos clave.
- **Vértices colgantes** (grado 1): 346, extremos de caminos que terminan en localidades.
- **Nodos clave en la topología**: la columna `nodos_clave.vertice` guarda el vértice que
  representa a cada nodo.

### Tablas resultantes

Primeras filas de la tabla de enlaces `red` después de `pgr_createTopology` (`source` y
`target` asignados, `prob_falla` en 0 por defecto):

```
 id | capa  | sintetico | source | target | largo_m | prob_falla
----+-------+-----------+--------+--------+---------+------------
  1 | fibra | f         |   1130 |   1155 |    4823 |          0
  2 | fibra | f         |   1155 |   1169 |    4917 |          0
  3 | fibra | f         |   1169 |   1187 |    7871 |          0
  4 | fibra | f         |   1187 |   1255 |    6917 |          0
  5 | fibra | f         |   1255 |   1304 |    6229 |          0
```

Primeras filas de la tabla de vértices `red_vertices_pgr` (4.583 vértices; geometría en
EPSG:32719, mostrada en lon/lat). Los primeros son de Isla de Pascua porque los vértices se
numeran de oeste a este (ver el paso 7):

```
 id |    lon    |   lat
----+-----------+----------
  1 | -109.4392 | -27.1597
  2 | -109.4367 | -27.1555
  3 | -109.4386 | -27.1647
  4 | -109.4295 | -27.1491
  5 | -109.4431 | -27.1866
```

## Enlaces sintéticos y limitaciones de los datos

- **Fibra incompleta**: el archivo SAIP contiene ~10.300 km de fibra, mientras que el Estudio
  documentó ~28.000 km recorridos (cuadro 4.1, p. 24). El levantamiento es visual (solo fibra
  aérea visible desde el camino) y no cubre todas las rutas. **Usando solo la fibra, la red tiene
  123 componentes y los 17 nodos clave quedarían repartidos en 15 de ellas**: el ATTR sería
  prácticamente 0, lo que contradice que la red troncal Arica–Puerto Montt existe y opera
  (SUBTEL, Estudio p. 22).
- Por eso se incorporan las demás rutas físicas documentadas (postación, caminos, ferrys) como
  **enlaces sintéticos**: representan tramos por donde la fibra no fue detectada pero que el
  propio Estudio integra en su grafo de la red física (p. 39). Quedan marcados con
  `sintetico = true` y se distinguen en el mapa.
- El **núcleo urbano de Santiago** no fue levantado (los anillos urbanos no vienen en los
  datos), así que se conecta con un enlace de acceso de 9,2 km.
- La **conexión entre el bloque norte-centro y el sur** pasa por un único puente sintético de
  2,6 km en San Antonio. En los datos no aparece la Ruta 5 entre Santiago y Rancagua, por lo que
  la red resultante es más frágil que la real en ese corredor.
- Los cables submarinos y el enlace terrestre a Argentina no se modelan como enlaces; sus puntos
  de llegada (Arica, Valparaíso, Los Andes) están representados como nodos clave.
