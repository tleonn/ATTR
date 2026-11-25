# ATTR: Average Two-Terminal Reliability

```bash
python scripts/attr.py --escenario operacion          # infraestructura en operación
python tests/test_attr.py                             # validación con casos teóricos
```

## Definición

Sea G = (V, E) la topología (tabla `red`), donde cada enlace e falla de forma independiente con
probabilidad p_e (columna `prob_falla`), y sea K ⊆ V el conjunto de nodos clave
(`nodos_clave.vertice`, |K| = 17). La **confiabilidad de dos terminales** de un par (s, t) es la
probabilidad de que, después de las fallas, exista al menos un camino entre s y t:

$$R_{st} = \Pr\left[\, s \leftrightarrow t \text{ en } G' \right], \qquad G' = (V, \{e \in E : e \text{ no falla}\})$$

El **ATTR** es el promedio de R_st sobre todos los pares no ordenados de nodos clave:

$$\mathrm{ATTR} = \binom{|K|}{2}^{-1} \sum_{\{s,t\} \subseteq K} R_{st} = \frac{2}{|K|(|K|-1)} \sum_{s<t} R_{st}$$

Con 17 nodos clave hay 136 pares. ATTR = 1 significa que todos los pares quedan conectados con
certeza; ATTR = 0, que ningún par queda conectado.

**Referencias**
- S. Neumayer y E. Modiano, *"Network Reliability With Geographically Correlated Failures"*,
  IEEE INFOCOM 2010, pp. 1658–1666, doi:10.1109/INFCOM.2010.5461984. Usa el ATTR como métrica de la red de fibra ante fallas geográficas
  (terremotos, ataques), que es exactamente el escenario de esta tarea.
- C. J. Colbourn, *The Combinatorics of Network Reliability*, Oxford University Press, 1987
  (confiabilidad de dos terminales).
- J. S. Provan y M. O. Ball, *"The Complexity of Counting Cuts and of Computing the Probability
  that a Graph is Connected"*, SIAM J. Computing 12(4), 1983. Calcular R_st exactamente es
  #P-completo, lo que justifica usar Monte Carlo en redes grandes.

## Método (`scripts/attr.py`)

1. **Lectura desde la BD**: `source`, `target` y `prob_falla` de cada enlace de `red`, y el
   vértice de cada nodo clave.
2. **Contracción exacta**: los enlaces con p = 0 nunca fallan, así que sus extremos se fusionan
   (union-find); los enlaces con p = 1 siempre fallan y se eliminan. Esto no cambia ningún R_st y
   reduce el problema a los enlaces con 0 < p < 1.
3. **Cálculo**:
   - **Exacto** si quedan ≤ 16 enlaces aleatorios: se enumeran los 2^m estados y se suma la
     probabilidad de cada estado en que s y t quedan conectados. En el escenario de operación
     m = 0, así que el resultado es exacto.
   - **Monte Carlo** en otro caso: en cada iteración se sortea el estado de cada enlace
     (falla si U(0,1) < p_e), se calculan las componentes conexas de la red sobreviviente
     (`scipy.sparse.csgraph.connected_components`) y se cuenta qué pares de nodos clave quedan en
     la misma componente. R_st se estima como la fracción de iteraciones en que s y t quedaron
     conectados.
4. **Resultado**: se guarda en `attr_resultado` (ATTR, IC 95 %, método, iteraciones, semilla) y
   en `attr_par` (R_st de cada par), para comparar escenarios.

### Número de iteraciones: N = 20.000

En cada iteración, el ATTR muestral X_i (fracción de pares conectados) está acotado en [0, 1].
Por la **desigualdad de Hoeffding**:

$$\Pr\left[\,|\widehat{\mathrm{ATTR}} - \mathrm{ATTR}| \ge \varepsilon\,\right] \le 2e^{-2N\varepsilon^2}
\;\Rightarrow\; N \ge \frac{\ln(2/\delta)}{2\varepsilon^2}$$

Para un error ε = 0,01 con confianza 1 − δ = 95 %, se necesita N ≥ ln(40) / 0,0002 ≈ 18.445, que
se redondea a **20.000**. Esta cota no depende de la red ni de las probabilidades. Además, el
script reporta el intervalo de confianza empírico (1,96·σ/√N), que en la práctica es más
estrecho. Con semilla fija (`2010`) los resultados son reproducibles. 20.000 iteraciones sobre la
red completa tardan unos 3 s.

### Validación (`tests/test_attr.py`)

| Grafo (s → t)                          | Teórico | Exacto | Monte Carlo |
|----------------------------------------|--------:|-------:|------------:|
| Serie, 2 enlaces con p = 0,5           |  0,2500 | 0,2500 |      0,2477 |
| 2 caminos paralelos de 2 enlaces, p = 0,1 | 0,9639 | 0,9639 |    0,9635 |
| Puente de Wheatstone, p = 0,2          |  0,9114 | 0,9114 |      0,9106 |

El valor teórico del puente es R = 2q² + 2q³ − 5q⁴ + 2q⁵, con q = 1 − p.

## ATTR de la infraestructura en operación

```
Escenario: operacion
Enlaces: 5323  (con 0 < p < 1 tras contraer: 0)
Método: exacto (enumeración de estados)

ATTR = 1.0000

Todos los pares de nodos clave quedan conectados.
```

**Interpretación**: con la infraestructura en operación (todos los enlaces con
`prob_falla = 0`), los 17 nodos clave pertenecen a la misma componente conexa, así que los 136
pares están conectados con certeza y **ATTR = 1**. Ningún nodo clave queda desconectado.

Este valor depende de los enlaces sintéticos de la topología (ver
[`topologia.md`](topologia.md)). Usando solo la fibra detectada, los nodos clave quedarían
repartidos en 15 componentes y el ATTR sería **0,0147** (solo 2 de los 136 pares conectados), lo que refleja que el levantamiento de
fibra está incompleto y no que la red real esté desconectada.
