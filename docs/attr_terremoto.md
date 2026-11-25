# ATTR post terremoto 27F

```bash
python scripts/attr.py --escenario terremoto   # ATTR con red.prob_falla del 27F
python scripts/comparar_attr.py                # comparación, nodos y enlaces críticos
```

## Resultado

```
Escenario: terremoto
Enlaces: 5323  (con 0 < p < 1 tras contraer: 4748)
Método: Monte Carlo, 20000 iteraciones, semilla 2010

ATTR = 0.8113  (IC 95 %: ± 0.0034)
```

| Escenario | ATTR | Método |
|-----------|-----:|--------|
| En operación | **1,0000** | exacto (todos los p = 0) |
| Post 27F     | **0,8113 ± 0,0034** | Monte Carlo, 20.000 iteraciones |
| **Diferencia** | **−0,1887 (−18,9 %)** | |

El intervalo de confianza empírico (±0,0034) es más estrecho que la cota de Hoeffding usada para
fijar N (±0,01), así que la diferencia de −0,19 es claramente significativa.

**Interpretación**: después del terremoto, un par de nodos clave elegido al azar queda conectado
con probabilidad 0,81. Dicho de otro modo, en promedio el 19 % de los 136 pares pierde
conectividad física.

## Nodos clave más afectados

| Nodo | R promedio en operación | R promedio post 27F | Cambio |
|------|------:|------:|-------:|
| **Concepción**   | 1,0000 | 0,7412 | **−25,9 %** |
| **Chillán**      | 1,0000 | 0,7615 | **−23,9 %** |
| Temuco, Valdivia, Puerto Montt, Coyhaique, Punta Arenas | 1,0000 | 0,774 | −22,6 % |
| Rancagua         | 1,0000 | 0,8306 | −16,9 % |
| Talca            | 1,0000 | 0,8346 | −16,5 % |
| Valparaíso, Los Andes, Santiago, Arica, Iquique, Antofagasta, Copiapó, La Serena | 1,0000 | 0,844 | −15,6 % |

Los nodos forman **dos bloques**: el norte-centro (Arica → Talca) y el sur (Chillán → Punta
Arenas). Dentro de cada bloque los pares siguen casi siempre conectados; lo que se pierde es la
conexión **entre** bloques:

| Par | R post 27F |
|-----|-----:|
| Santiago – Rancagua | 0,968 |
| Rancagua – Talca | 0,974 |
| **Talca – Chillán** | **0,672** |
| Chillán – Concepción | 0,893 |
| Chillán – Temuco | 0,923 |
| Temuco – Punta Arenas | 0,999 |
| Santiago – Temuco | 0,654 |

El cuello de botella es el **corredor Talca–Chillán**, que cruza el Maule y Ñuble a 30–140 km del
epicentro. Todo el tráfico norte–sur pasa por ahí, así que su falla separa los 10 nodos del norte
de los 7 del sur (70 de los 136 pares). Concepción es el nodo más afectado porque, además, depende de su acceso propio
(p = 0,032) y de los tramos Chillán–Concepción.

## Enlaces más afectados

**Enlaces críticos individuales** (su falla aislada desconecta nodos clave):

|   id | Capa      | p falla | Pares desconectados | Pérdida esperada de ATTR | d epi (km) | Ubicación |
|-----:|-----------|--------:|-------:|------:|------:|-----------|
| 5319 | acceso*   | 0,0316 | 16 | 0,0037 |  79,5 | Concepción |
| 5318 | acceso*   | 0,0258 | 16 | 0,0030 |  89,4 | Chillán |
| 5317 | acceso*   | 0,0099 | 16 | 0,0012 | 135,6 | Talca |
| 1214 | fibra     | 0,0012 | 72 | 0,0006 | 237,1 | −34,17; −71,73 (O'Higgins) |
| 3014 | postación*| 0,0014 | 16 | 0,0002 | 228,4 | −34,33; −71,56 |
| 3013 | postación*| 0,0011 | 16 | 0,0001 | 238,7 | −34,30; −71,46 |
| 1517 | fibra     | 0,0010 | 16 | 0,0001 | 243,7 | −34,30; −71,39 |

Entre los 7 explican solo ~0,009 de la caída de 0,189. **La pérdida viene de fallas
combinadas**: en el corredor Talca–Chillán hay varias rutas alternativas (por la costa y por el
interior), cada una formada por decenas de enlaces en serie con p entre 0,02 y 0,08 (los enlaces de fibra
más afectados, con p ≈ 0,07, están en este corredor; ver [`prob_falla.md`](prob_falla.md)). Una
ruta en serie se corta si falla **cualquiera** de sus enlaces, así que la probabilidad de que
cada ruta se corte es alta, y la de que se corten todas a la vez (1 − 0,672 ≈ 0,33) explica la
mayor parte de la caída del ATTR: 70 pares × 0,33 / 136 ≈ 0,17 de los 0,19 perdidos. El corte más probable de un solo par de enlaces entre Santiago y Temuco
(fibra 684, p = 0,072, y fibra 1844, p = 0,026) tiene probabilidad 0,0019: no hay un único punto
débil, sino muchos cortes posibles que se suman.

## Contraste con lo ocurrido en el 27F

| Aspecto | Modelo | Lo observado (bibliografía) |
|---------|--------|-----------------------------|
| Zona afectada | Daño concentrado a < 150 km del epicentro: Maule y Ñuble/Biobío | *"About 70 % to 80 % of the cell sites in regions VII and VIII had problems with either equipment or antenna damage. This rate falls to about 50 % in region V"* (TCLEE, p. 9) |
| Nodo más afectado | Concepción (−25,9 %) | Cables de energía y telecomunicaciones dañados en el puente Juan Pablo II sobre el Biobío, en Concepción (TCLEE, p. 22) |
| Cortes de fibra | Fallas por sacudida en tendidos aéreos, mayores cerca del epicentro | *"fiber optic cables were severed in many locations mostly due to collocating on bridges and overpasses"* (TCLEE, p. 9); *"muchos puentes se cayeron, causando como daño adicional el corte de fibras que iban en su interior y cortando de raíz la conectividad en las ciudades afectadas"* (Estudio, p. 4) |
| Redundancia | ATTR = 0,81 > 0 gracias a rutas paralelas | *"alternative links provided by another company allowed to some transmission circuits for inter LATA operation"* (TCLEE, p. 9) |
| Alcance nacional | Norte y Santiago casi intactos (solo pierden la conexión con el sur) | *"más del 60 % de la Internet chilena quedó desconectado por alrededor de 6 horas esa madrugada [...] se debió a una mala ingeniería de las interconexiones y respaldos dentro de Santiago"* (Estudio, p. 10) |
| Energía | No modelada | *"by about 6:30 AM most cell sites and remotes sites ran out of power"*; solo las centrales de más de 5.000 abonados, las MTSO y las oficinas troncales de fibra tenían generadores (TCLEE, p. 8) |
| Recuperación | No modelada (escenario estático) | *"Both landline and wireless services were restored 7 days after the earthquake"* (TCLEE, p. 9) |

**Coincidencias**: el modelo identifica correctamente la zona más dañada (regiones VII y VIII de
la época, hoy Maule, Ñuble y Biobío) y a Concepción como el nodo clave más afectado. También
muestra que la redundancia de rutas evita una desconexión total, como ocurrió con los enlaces
alternativos de otros operadores.

**Diferencias**: el impacto real fue **mayor** que el −18,9 % del modelo, por causas que este
no representa:
1. **Energía**: la causa principal de la pérdida de servicio fue la falta de energía en sitios
   sin generador (baterías de 3–8 h).
2. **Puentes**: los cortes de fibra se concentraron en puentes y pasos sobre nivel, que son
   fallas puntuales y no dependen solo de la distancia al epicentro.
3. **Capa lógica**: la desconexión del 60 % de la Internet chilena se debió a interconexiones
   dentro de Santiago (capa IP/PIT), no a cortes físicos; el modelo solo evalúa la red física.
4. **Tsunami**: afectó la costa (Constitución, Talcahuano), y no está en el modelo.

## Limitaciones del modelo

- **Distancia al epicentro vs. ruptura**: la ruptura de ~500 km hace que la PGA real en
  Concepción, Talca y la zona central sea mayor que la estimada desde el epicentro. Con una
  distancia a la ruptura, la caída del ATTR sería mayor.
- **Segmentación de los enlaces**: p se aplica a cada enlace de la topología tal como quedó
  digitalizado y nodado (mediana de ~3,8 km en la zona afectada), no por kilómetro. Una ruta
  dividida en más segmentos acumula más probabilidad de corte, lo que puede sobrestimar la falla
  de corredores muy segmentados.
- **Independencia**: se supone que los enlaces fallan de forma independiente, aunque los
  enlaces cercanos sufren el mismo movimiento (fallas correlacionadas).
- **Enlaces sintéticos**: el 63 % de los km son rutas sin fibra detectada (postación, caminos,
  ferrys). El ATTR depende de suponer que esas rutas existen y operan.
- **Infraestructura de 2019**: los datos son posteriores al 27F (2010); la red de 2010 era menos
  extensa y probablemente menos redundante.
- **Nodos sin falla**: los nodos clave (PIT, data centers, aterrizajes) se suponen intactos; solo
  fallan los enlaces.

## Referencias

- ASCE TCLEE, *Preliminary Report: 27 February 2010 Mw8.8 Offshore Maule, Chile Earthquake*,
  Modified ASCE TCLEE Chile web report (EERI), mayo 2010. A. Tang (team lead), A. Kwasinski,
  L. Dueñas-Osorio, J. Eidinger, A. Schiff et al.
  <https://lfestorage.s3.us-east-2.amazonaws.com/images/2010_02_27_chile/pdfs/TCLEE-Web-Report-EERI-v1.pdf>
- NIC Chile Research Labs, *Estudio y Recomendaciones sobre la Resiliencia de la infraestructura
  de la Internet chilena*, proyecto CORFO 15BPE-47225 (archivo `Yafun.pdf`), pp. 4 y 10.
