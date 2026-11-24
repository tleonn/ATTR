# Terremoto 27F y modelo de falla

## 1. Sismo Mw 8.8 desde USGS

```bash
python scripts/cargar_sismo.py
```

El evento se obtiene de la API FDSN del USGS Earthquake Catalog (la misma que usa
<https://earthquake.usgs.gov/earthquakes/search/>):

```
https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&starttime=2010-02-27&endtime=2010-02-28&minmagnitude=8.5
```

La consulta devuelve un único evento, con ID **`official20100227063411530_30`**
([página del evento](https://earthquake.usgs.gov/earthquakes/eventpage/official20100227063411530_30)).
El GeoJSON queda versionado en `data/sismo_27F.geojson`, para que el flujo funcione sin conexión,
y se carga en la tabla `sismo` (los atributos en columnas y el GeoJSON completo en `jsonb`):

```
              id              |            lugar             | magnitud |         fecha_utc         | profundidad_km |       st_astext
------------------------------+------------------------------+----------+---------------------------+----------------+------------------------
 official20100227063411530_30 | 2010 Maule, Chile Earthquake |      8.8 | 2010-02-27 06:34:11.53+00 |           22.9 | POINT(-72.898 -36.122)
```

Mw 8,8 (`mww`), 27-02-2010 a las 06:34:11 UTC (03:34 hora de Chile), epicentro frente a la costa
del Maule (−36,122; −72,898) y profundidad de 22,9 km.

## 2. Modelo de falla probabilístico

El modelo combina dos funciones de la literatura:

**sismo (M, H) → distancia al epicentro → PGA en el enlace (atenuación) → probabilidad de falla
(curva de fragilidad)**

### 2.1 Atenuación de PGA: Youngs et al. (1997)

> R. R. Youngs, S.-J. Chiou, W. J. Silva y J. R. Humphrey, *"Strong Ground Motion Attenuation
> Relationships for Subduction Zone Earthquakes"*, Seismological Research Letters 68(1),
> 58–73, 1997.

Es una relación de atenuación desarrollada específicamente para **sismos de subducción**,
calibrada con registros de Chile, Perú, México, Japón y Alaska. Se usa en los mapas de amenaza
del USGS y está implementada en OpenQuake (`YoungsEtAl1997SInter`). Para roca:

$$\ln \mathrm{PGA} = 0{,}2418 + 1{,}414\,M + C_1 + C_2(10-M)^3 + C_3 \ln\!\left(R + 1{,}7818\,e^{0{,}554M}\right) + 0{,}00607\,H + 0{,}3846\,Z_t$$

| Parámetro | Valor | Origen |
|-----------|------:|--------|
| M | 8,8 | Magnitud Mww del evento USGS |
| H | 22,9 km | Profundidad del hipocentro (USGS) |
| Z_t | 0 | Tipo de fuente: 0 = interfaz (el 27F fue un sismo de interfaz, mecanismo inverso); 1 = intraplaca |
| C₁, C₂, C₃ | 0; 0; −2,552 | Coeficientes de PGA en roca (Youngs et al., 1997, tabla de roca) |
| R | √(d² + H²) km | Distancia hipocentral, con d = distancia del enlace al epicentro |
| σ (ln PGA) | 1,45 − 0,1·min(M, 8) = 0,65 | Desviación estándar del modelo (C₄ = 1,45, C₅ = −0,1; la magnitud se limita a 8) |

### 2.2 Curva de fragilidad: HAZUS, circuitos de distribución

> FEMA, *Hazus Earthquake Model Technical Manual* (Hazus 4.2 SP3), cap. 8 "Utility Systems",
> sección 8.5.6.2, **Tabla 8-30** "Peak Ground Acceleration Fragility Functions for
> Distribution Circuits", p. 8-62.

HAZUS define una fragilidad lognormal por estado de daño ds:

$$P(DS \ge ds \mid \mathrm{PGA}) = \Phi\!\left(\frac{\ln(\mathrm{PGA}/\theta_{ds})}{\beta_{ds}}\right)$$

| Estado de daño | θ mediana (g) | β | Fracción de circuitos que falla (HAZUS §8.5.4) |
|----------------|-------------:|----:|------------------:|
| Leve           | 0,24 | 0,25 |  4 % |
| Moderado       | 0,33 | 0,20 | 12 % |
| Extensivo      | 0,58 | 0,15 | 50 % |
| Completo       | 0,89 | 0,15 | 80 % |

Se usan los valores de **componentes sin anclaje / estándar** (*Unanchored/Standard Components*).

### 2.3 Probabilidad de falla de un enlace

La PGA real en un punto es lognormal en torno a la mediana de Youngs (dispersión σ). Al
combinarla con la fragilidad lognormal, la probabilidad de alcanzar cada estado de daño queda:

$$P_{ds}(d) = \Phi\!\left(\frac{\ln\left(\mathrm{PGA}(d)/\theta_{ds}\right)}{\sqrt{\beta_{ds}^2 + \sigma^2}}\right)$$

Como HAZUS define cada estado de daño por la fracción de circuitos que falla, la probabilidad de
falla de un enlace es la **fracción esperada de circuitos que fallan**:

$$p_e = 0{,}04\,(P_L - P_M) + 0{,}12\,(P_M - P_E) + 0{,}50\,(P_E - P_C) + 0{,}80\,P_C$$

donde d es la distancia mínima del enlace e al epicentro (`ST_Distance` sobre la geometría
proyectada en metros, en la etapa siguiente).

Curva resultante (`python scripts/modelo_falla.py`):

| d epicentro (km) | PGA (g) | P(≥leve) | P(≥mod) | P(≥ext) | P(≥comp) | **p falla** |
|-----:|------:|------:|------:|------:|------:|-------:|
|   0 | 0,264 | 0,555 | 0,372 | 0,119 | 0,034 | **0,108** |
|  25 | 0,237 | 0,494 | 0,314 | 0,090 | 0,024 | **0,086** |
|  50 | 0,196 | 0,385 | 0,221 | 0,052 | 0,012 | **0,056** |
|  75 | 0,160 | 0,281 | 0,144 | 0,027 | 0,005 | **0,035** |
| 100 | 0,132 | 0,197 | 0,090 | 0,013 | 0,002 | **0,021** |
| 150 | 0,094 | 0,088 | 0,032 | 0,003 | 0,000 | **0,007** |
| 200 | 0,069 | 0,036 | 0,011 | 0,001 | 0,000 | **0,003** |
| 300 | 0,041 | 0,005 | 0,001 | 0,000 | 0,000 | **0,000** |

### 2.4 Justificación de la adaptación a enlaces de fibra

- **La fibra chilena es mayoritariamente aérea sobre postes**: según SUBTEL (Estudio, p. 22),
  las redes de transporte *"están principalmente desplegadas en forma aérea"*, y el Estudio
  documenta la fibra junto a la postación eléctrica y telefónica (cuadro 4.1). Un circuito de
  distribución de HAZUS es justamente *"poles, wires, in-line equipment [...] above ground and
  underground conductors"* (§8.5.3.2). Un tramo de fibra aérea comparte la misma estructura
  (postes, tendido, herrajes), así que falla por las mismas causas: caída o inclinación de
  postes, cortes por tensión del tendido y daño en cruces y puentes.
- **Componentes sin anclaje**: la postación en caminos rurales y secundarios no tiene diseño
  sísmico, así que se usa la clase "Unanchored/Standard", más frágil y conservadora.
- **Fracción de circuitos → probabilidad por enlace**: HAZUS expresa el daño como porcentaje de
  circuitos fallados en una zona con cierta PGA. Interpretar ese porcentaje como la probabilidad
  de que un enlace de esa zona falle es directo, y entrega un p_e ∈ [0; 0,8] sin introducir
  umbrales arbitrarios.
- **Desde el epicentro**: la atenuación usa la distancia al epicentro (hipocentral, con H), como
  pide el enunciado. Se usa la distancia **mínima** del enlace al epicentro, es decir, la PGA
  máxima que experimenta el tramo (criterio conservador).
- **Enlaces sintéticos**: se les aplica el mismo modelo. Representan tendidos aéreos sobre
  postación o caminos donde la fibra no fue detectada (ver `topologia.md`).

### 2.5 Limitaciones

- **Fuente puntual vs. ruptura extendida**: el 27F rompió unos 450–500 km de la interfaz (desde
  la península de Arauco hasta la zona de Valparaíso). Youngs et al. definen R como distancia a
  la ruptura; usar la distancia al epicentro (como pide el enunciado) **subestima** la PGA en los
  extremos de la ruptura (Concepción, Santiago, Valparaíso).
- **Extrapolación en magnitud**: la base de datos de Youngs et al. llega a M ≈ 8,2; para M 8,8
  el término de saturación (1,7818·e^{0,554M}) limita la PGA cerca de la fuente (0,26 g de
  mediana en el epicentro), mientras que los registros reales del 27F fueron mayores en varias
  estaciones.
- **Roca vs. suelo**: se usan los coeficientes de roca; no se consideran efectos de sitio
  (amplificación en suelos blandos), licuefacción, deslizamientos ni el tsunami, que también
  cortaron enlaces en el 27F.
- **Independencia**: el ATTR supone fallas independientes entre enlaces, aunque los enlaces
  cercanos están expuestos al mismo movimiento (fallas correlacionadas).
- **Energía**: no se modela la caída de la red eléctrica, que en el 27F fue una causa principal
  de pérdida de servicio de telecomunicaciones.
