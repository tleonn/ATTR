import argparse
import itertools
import math

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

from db import conectar

ITERACIONES = 20000
SEMILLA = 2010
MAX_EXACTO = 16


class UnionFind:
    def __init__(self):
        self.padre = {}

    def buscar(self, x):
        self.padre.setdefault(x, x)
        while self.padre[x] != x:
            self.padre[x] = self.padre[self.padre[x]]
            x = self.padre[x]
        return x

    def unir(self, a, b):
        self.padre[self.buscar(a)] = self.buscar(b)


def cargar_grafo(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT source, target, prob_falla FROM red WHERE source IS NOT NULL ORDER BY id")
        enlaces = cur.fetchall()
        cur.execute("SELECT nombre, vertice FROM nodos_clave ORDER BY id")
        nodos = cur.fetchall()
    return enlaces, nodos


def contraer(enlaces, vertices_clave):
    """Fusiona los enlaces que nunca fallan (p = 0) y descarta los que siempre fallan (p = 1)."""
    uf = UnionFind()
    for v in vertices_clave:
        uf.buscar(v)
    for s, t, p in enlaces:
        uf.buscar(s), uf.buscar(t)
        if p <= 0:
            uf.unir(s, t)

    indice = {}
    def idx(v):
        return indice.setdefault(uf.buscar(v), len(indice))

    clave = np.array([idx(v) for v in vertices_clave])
    aleatorios = [(idx(s), idx(t), p) for s, t, p in enlaces
                  if 0 < p < 1 and uf.buscar(s) != uf.buscar(t)]
    for s, t, _ in aleatorios:
        idx(s), idx(t)
    return len(indice), clave, aleatorios


def conectados(n, clave, origen, destino):
    """Matriz booleana K x K: qué pares de nodos clave quedan en la misma componente."""
    grafo = coo_matrix((np.ones(len(origen)), (origen, destino)), shape=(n, n))
    _, etiqueta = connected_components(grafo, directed=False)
    e = etiqueta[clave]
    return e[:, None] == e[None, :]


def attr_exacto(n, clave, aleatorios):
    k = len(clave)
    r = np.zeros((k, k))
    origen = np.array([a for a, _, _ in aleatorios], dtype=int)
    destino = np.array([b for _, b, _ in aleatorios], dtype=int)
    p = np.array([q for _, _, q in aleatorios])
    for estado in itertools.product([True, False], repeat=len(aleatorios)):
        vivo = np.array(estado, dtype=bool)
        prob = np.prod(np.where(vivo, 1 - p, p)) if len(p) else 1.0
        r += prob * conectados(n, clave, origen[vivo] if len(p) else origen,
                               destino[vivo] if len(p) else destino)
    return r, 0.0


def attr_monte_carlo(n, clave, aleatorios, iteraciones, semilla):
    rng = np.random.default_rng(semilla)
    k = len(clave)
    origen = np.array([a for a, _, _ in aleatorios], dtype=int)
    destino = np.array([b for _, b, _ in aleatorios], dtype=int)
    p = np.array([q for _, _, q in aleatorios])
    triu = np.triu_indices(k, 1)
    r = np.zeros((k, k))
    muestras = np.empty(iteraciones)
    for i in range(iteraciones):
        vivo = rng.random(len(p)) >= p
        c = conectados(n, clave, origen[vivo], destino[vivo])
        r += c
        muestras[i] = c[triu].mean()
    error = 1.96 * muestras.std(ddof=1) / math.sqrt(iteraciones)
    return r / iteraciones, error


def calcular_attr(conn, iteraciones=ITERACIONES, semilla=SEMILLA):
    enlaces, nodos = cargar_grafo(conn)
    nombres = [n for n, _ in nodos]
    n, clave, aleatorios = contraer(enlaces, [v for _, v in nodos])

    if len(aleatorios) <= MAX_EXACTO:
        metodo, iters = "exacto", None
        r, error = attr_exacto(n, clave, aleatorios)
    else:
        metodo, iters = "monte carlo", iteraciones
        r, error = attr_monte_carlo(n, clave, aleatorios, iteraciones, semilla)

    k = len(nombres)
    pares = [(nombres[i], nombres[j], float(r[i, j])) for i, j in zip(*np.triu_indices(k, 1))]
    attr = sum(x for _, _, x in pares) / len(pares)
    return {
        "attr": attr, "ic95": float(error), "metodo": metodo, "iteraciones": iters,
        "semilla": semilla if iters else None, "enlaces": len(enlaces),
        "enlaces_aleatorios": len(aleatorios), "nodos": nombres, "pares": pares,
    }


def guardar(conn, escenario, res):
    with conn.cursor() as cur:
        cur.execute(
            """CREATE TABLE IF NOT EXISTS attr_resultado (
                   escenario text PRIMARY KEY, attr double precision, ic95 double precision,
                   metodo text, iteraciones integer, semilla integer,
                   enlaces integer, enlaces_aleatorios integer, calculado timestamptz DEFAULT now())"""
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS attr_par (
                   escenario text, nodo_a text, nodo_b text, confiabilidad double precision,
                   PRIMARY KEY (escenario, nodo_a, nodo_b))"""
        )
        cur.execute("DELETE FROM attr_resultado WHERE escenario = %s", (escenario,))
        cur.execute("DELETE FROM attr_par WHERE escenario = %s", (escenario,))
        cur.execute(
            "INSERT INTO attr_resultado VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (escenario, res["attr"], res["ic95"], res["metodo"], res["iteraciones"],
             res["semilla"], res["enlaces"], res["enlaces_aleatorios"]),
        )
        cur.executemany(
            "INSERT INTO attr_par VALUES (%s,%s,%s,%s)",
            [(escenario, a, b, x) for a, b, x in res["pares"]],
        )
    conn.commit()


def imprimir(escenario, res):
    print(f"Escenario: {escenario}")
    print(f"Enlaces: {res['enlaces']}  (con 0 < p < 1 tras contraer: {res['enlaces_aleatorios']})")
    if res["metodo"] == "exacto":
        print("Método: exacto (enumeración de estados)")
    else:
        print(f"Método: Monte Carlo, {res['iteraciones']} iteraciones, semilla {res['semilla']}")
    print(f"\nATTR = {res['attr']:.4f}" + (f"  (IC 95 %: ± {res['ic95']:.4f})" if res["ic95"] else ""))

    k = len(res["nodos"])
    prom = {n: 0.0 for n in res["nodos"]}
    for a, b, x in res["pares"]:
        prom[a] += x / (k - 1)
        prom[b] += x / (k - 1)
    print("\nConfiabilidad promedio de cada nodo clave con el resto:")
    for nombre, x in sorted(prom.items(), key=lambda t: t[1]):
        print(f"  {nombre:<14}{x:.4f}")

    peores = sorted(res["pares"], key=lambda t: t[2])[:10]
    if peores[0][2] < 1:
        print("\nPares con menor probabilidad de quedar conectados:")
        for a, b, x in peores:
            print(f"  {a:<14}- {b:<14}{x:.4f}")
    else:
        print("\nTodos los pares de nodos clave quedan conectados.")


def main():
    parser = argparse.ArgumentParser(description="ATTR entre los nodos clave")
    parser.add_argument("--escenario", default="operacion")
    parser.add_argument("--iteraciones", type=int, default=ITERACIONES)
    parser.add_argument("--semilla", type=int, default=SEMILLA)
    args = parser.parse_args()

    conn = conectar()
    res = calcular_attr(conn, args.iteraciones, args.semilla)
    guardar(conn, args.escenario, res)
    imprimir(args.escenario, res)
    conn.close()


if __name__ == "__main__":
    main()
