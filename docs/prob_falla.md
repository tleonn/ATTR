# Probabilidad de falla de cada enlace

```bash
python scripts/prob_falla.py
```

## Implementación

`sql/02_prob_falla.sql` implementa el modelo de [`sismo_modelo_falla.md`](sismo_modelo_falla.md)
como funciones de PostgreSQL y actualiza la tabla `red`:

| Función SQL | Calcula |
|-------------|---------|
| `pga_youngs(d_km, M, H)` | Mediana de PGA (g), Youngs et al. (1997), roca, interfaz |
| `fragilidad(pga, θ, β, σ)` | P(DS ≥ ds) = Φ(ln(PGA/θ) / √(β² + σ²)), con Φ(x) = ½(1 + erf(x/√2)) |
| `prob_falla_sismo(d_km, M, H)` | p = 0,04(P_L−P_M) + 0,12(P_M−P_E) + 0,50(P_E−P_C) + 0,80·P_C (HAZUS Tabla 8-30) |

```sql
UPDATE red r
SET dist_epicentro_km = ST_Distance(r.geom, ST_Transform(s.geom, 32719)) / 1000,
    pga_g             = pga_youngs(..., s.magnitud, s.profundidad_km),
    prob_falla        = prob_falla_sismo(..., s.magnitud, s.profundidad_km)
FROM sismo s
WHERE s.id = 'official20100227063411530_30';
```

- **Distancia**: `ST_Distance` entre la geometría del enlace y el epicentro, ambos en
  **EPSG:32719 (metros)**. Es la distancia mínima del tramo al epicentro, es decir, el punto del
  enlace con mayor PGA.
- **Parámetros del sismo**: M y H se leen de la tabla `sismo` (cargada desde USGS), no están fijos
  en el código.
- **Funciones SQL**: al estar en la BD, `main.sql` puede recalcular las probabilidades sin
  Python. `erf()` es nativa desde PostgreSQL 16.
- Se agregan las columnas `dist_epicentro_km` y `pga_g` a `red`, para usarlas en el mapa.

### Verificación

- **SQL vs Python**: el script compara 200 enlaces al azar contra `scripts/modelo_falla.py`, con
  un error máximo de ~4·10⁻¹⁷ (precisión de máquina).
- **Proyección vs geodésica**: usar UTM 19S en lugar de la distancia geodésica cambia p en
  como máximo **6·10⁻⁵**:

| Distancia al epicentro | Enlaces | Dif. máx. distancia | Dif. máx. p |
|------------------------|--------:|--------------------:|------------:|
| < 100 km               |     295 | 0,12 km             | 6,3·10⁻⁵ |
| 100 – 300 km           |   1.130 | 0,40 km             | 5,2·10⁻⁵ |
| 300 – 1.000 km         |   1.850 | 1,13 km             | 2·10⁻⁶   |
| > 1.000 km             |   2.048 | hasta 274 km (Isla de Pascua, fuera de la zona UTM) | 0 |

## Resultados

```
Enlaces: 5323  |  con p > 0,0001: 1703
p mín = 0.00e+00  p media = 0.0035  p máx = 0.1047
Km de red que se espera fallen (Σ p·largo): 79 km
```

### Distribución

| Probabilidad de falla | Enlaces |     km |
|-----------------------|--------:|-------:|
| ≤ 0,0001              |   3.606 | 20.448 |
| 0,0001 – 0,001        |     566 |  2.262 |
| 0,001 – 0,01          |     584 |  2.492 |
| 0,01 – 0,05           |     474 |  1.955 |
| 0,05 – 0,1            |      71 |    305 |
| > 0,1                 |       8 |     25 |

### Por capa

| Capa        | Enlaces | p > 0,01 | p media | p máx  |
|-------------|--------:|---------:|--------:|-------:|
| postación*  |   1.422 |      146 |  0,0042 | 0,1047 |
| camino*     |   1.407 |       55 |  0,0014 | 0,1046 |
| fibra       |   2.251 |      346 |  0,0047 | 0,0757 |
| acceso*     |      15 |        2 |  0,0046 | 0,0316 |
| ferry*      |     227 |        4 |  0,0003 | 0,0168 |
| puente*     |       1 |        0 |  0,0003 | 0,0003 |

\* sintético

### Enlaces más afectados

Caminos con postación en la costa de Ñuble, en torno a Cobquecura, a 8–17 km del epicentro:

|   id | Capa        | Largo (m) | d epi (km) | PGA (g) | p falla | Lat, Lon |
|-----:|-------------|----------:|-----------:|--------:|--------:|----------|
| 3315 | postación*  | 3.312 |  8,2 | 0,261 | 0,105 | −36,111; −72,806 |
| 4919 | camino*     | 1.360 |  8,4 | 0,261 | 0,105 | −36,092; −72,807 |
| 3316 | postación*  | 1.397 |  9,0 | 0,260 | 0,104 | −36,128; −72,795 |
| 3317 | postación*  | 4.622 |  9,3 | 0,260 | 0,104 | −36,140; −72,781 |
| 3314 | postación*  | 5.019 |  9,4 | 0,260 | 0,104 | −36,080; −72,793 |
| 3313 | postación*  | 3.472 | 12,1 | 0,257 | 0,101 | −36,059; −72,774 |
| 3319 | postación*  | 5.579 | 12,6 | 0,256 | 0,101 | −36,144; −72,731 |
| 3312 | postación*  | 4.224 | 14,1 | 0,254 | 0,100 | −36,028; −72,774 |
| 3311 | postación*  | 2.228 | 16,9 | 0,250 | 0,096 | −36,002; −72,771 |

### Enlaces de fibra (reales) más afectados

Tendidos de fibra entre Chillán, Quirihue y la costa, a 33–40 km del epicentro:

|  id | Largo (m) | d epi (km) | PGA (g) | p falla | Lat, Lon |
|----:|----------:|-----------:|--------:|--------:|----------|
| 288 | 12.640 | 33,3 | 0,223 | 0,076 | −36,214; −72,510 |
| 599 |  4.299 | 34,4 | 0,222 | 0,074 | −36,265; −72,546 |
| 680 |  3.051 | 36,5 | 0,218 | 0,072 | −36,294; −72,548 |
| 600 |  5.164 | 36,9 | 0,217 | 0,071 | −36,386; −72,638 |
| 289 | 10.250 | 37,1 | 0,217 | 0,071 | −36,341; −72,581 |
|  22 |  3.528 | 38,8 | 0,214 | 0,069 | −35,835; −72,623 |
| 601 |  4.317 | 38,8 | 0,214 | 0,069 | −36,419; −72,651 |
| 287 |  8.208 | 39,5 | 0,213 | 0,068 | −36,159; −72,455 |
| 602 |  1.713 | 39,8 | 0,212 | 0,068 | −36,433; −72,675 |
| 603 |  4.926 | 39,8 | 0,212 | 0,068 | −36,454; −72,691 |

### Enlaces menos afectados

3.606 enlaces (20.448 km, 74 % de la red) tienen p ≤ 0,0001: todo el Norte Grande, la zona
austral e Isla de Pascua, a más de ~400 km del epicentro. Los más lejanos son los de Isla de
Pascua (~3.580 km geodésicos), con p = 0.

## Lectura

- El daño se concentra en un radio de ~150 km alrededor del epicentro (Maule y Ñuble, y en
  menor medida el Biobío): 553 enlaces (~2.285 km) tienen p > 0,01.
- La probabilidad máxima es 0,105 porque, con el epicentro a 22,9 km de profundidad, la mediana
  de PGA no supera 0,26 g, por debajo de la mediana del estado "moderado" (0,33 g).
- Concepción (~79 km del epicentro) y Santiago (~362 km) quedan con probabilidades bajas porque
  el modelo usa la distancia al epicentro y no a la ruptura completa (ver limitaciones en
  `sismo_modelo_falla.md`).
