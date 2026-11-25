import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

from db import conectar

P_MIN = 0.001


def resultados(cur):
    cur.execute("SELECT escenario, attr, ic95, metodo, iteraciones FROM attr_resultado")
    return {e: (a, ic, m, it) for e, a, ic, m, it in cur.fetchall()}


def comparar(cur):
    r = resultados(cur)
    a0, a1 = r["operacion"][0], r["terremoto"][0]
    print(f"ATTR en operación : {a0:.4f}  ({r['operacion'][2]})")
    print(f"ATTR post 27F     : {a1:.4f}  ± {r['terremoto'][1]:.4f}  "
          f"({r['terremoto'][2]}, {r['terremoto'][3]} iteraciones)")
    print(f"Diferencia        : {a1 - a0:+.4f}  ({(a1 - a0) / a0 * 100:+.1f} %)")


def nodos(cur):
    cur.execute(
        """WITH p AS (SELECT escenario, nodo_a AS nodo, confiabilidad FROM attr_par
                      UNION ALL SELECT escenario, nodo_b, confiabilidad FROM attr_par)
           SELECT nodo, avg(confiabilidad) FILTER (WHERE escenario = 'operacion'),
                        avg(confiabilidad) FILTER (WHERE escenario = 'terremoto')
           FROM p GROUP BY nodo ORDER BY 3"""
    )
    print("\nConfiabilidad promedio de cada nodo clave con el resto:")
    print(f"  {'nodo':<14}{'operación':>10}{'post 27F':>10}{'cambio':>9}")
    for nodo, r0, r1 in cur.fetchall():
        print(f"  {nodo:<14}{r0:>10.4f}{r1:>10.4f}{(r1 - r0) / r0 * 100:>8.1f}%")


def criticos(cur, top=10):
    """Quita cada enlace con p > P_MIN y cuenta los pares de nodos clave que se desconectan."""
    cur.execute("SELECT id, source, target, prob_falla FROM red ORDER BY id")
    enlaces = np.array(cur.fetchall(), dtype=float)
    cur.execute("SELECT vertice FROM nodos_clave ORDER BY id")
    clave = np.array([v for (v,) in cur.fetchall()], dtype=int)
    n = int(enlaces[:, 1:3].max()) + 1
    k = len(clave)
    pares = k * (k - 1) // 2

    def desconectados(mascara):
        s, t = enlaces[mascara, 1].astype(int), enlaces[mascara, 2].astype(int)
        _, et = connected_components(coo_matrix((np.ones(len(s)), (s, t)), shape=(n, n)),
                                     directed=False)
        e = et[clave]
        return pares - int(np.triu(e[:, None] == e[None, :], 1).sum())

    base = desconectados(np.ones(len(enlaces), dtype=bool))
    filas = []
    for i in np.where(enlaces[:, 3] > P_MIN)[0]:
        m = np.ones(len(enlaces), dtype=bool)
        m[i] = False
        d = desconectados(m) - base
        if d:
            filas.append((int(enlaces[i, 0]), enlaces[i, 3], d))
    filas.sort(key=lambda f: f[1] * f[2], reverse=True)

    print(f"\nEnlaces críticos: {len(filas)} enlaces con p > {P_MIN} cuya falla aislada "
          f"desconecta nodos clave")
    print(f"  {'id':>5} {'capa':<11}{'p falla':>8}{'pares':>7}{'pérdida ATTR':>14}"
          f"{'d epi km':>10}  lat, lon")
    for id_, p, d in filas[:top]:
        cur.execute(
            """SELECT capa || CASE WHEN sintetico THEN '*' ELSE '' END, dist_epicentro_km,
                      ST_Y(ST_Transform(ST_Centroid(geom), 4326)),
                      ST_X(ST_Transform(ST_Centroid(geom), 4326))
               FROM red WHERE id = %s""", (id_,))
        capa, d_epi, lat, lon = cur.fetchone()
        print(f"  {id_:>5} {capa:<11}{p:>8.4f}{d:>7}{p * d / pares:>14.4f}{d_epi:>10.1f}"
              f"  {lat:.3f}, {lon:.3f}")
    return filas


def main():
    conn = conectar()
    with conn.cursor() as cur:
        comparar(cur)
        nodos(cur)
        criticos(cur)
    conn.close()


if __name__ == "__main__":
    main()
