from db import conectar, ejecutar_sql

TOLERANCIA = 10 


def notices(conn):
    for n in conn.notices:
        print("   ", n.strip())
    conn.notices.clear()


def crear_topologia(conn):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT pgr_createTopology('red', %s, 'geom', 'id', clean := true)",
            (TOLERANCIA,),
        )
        estado = cur.fetchone()[0]
        cur.execute(
            """UPDATE red SET largo_m = ST_Length(ST_Transform(geom, 4326)::geography),
                              cost = ST_Length(ST_Transform(geom, 4326)::geography),
                              reverse_cost = ST_Length(ST_Transform(geom, 4326)::geography)"""
        )
    conn.commit()
    return estado


def agregar_accesos(conn):
    """Tramo sintético nodo clave -> vértice/tramo más cercano (sobre la red ya nodada)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO red (capa, sintetico, geom)
            SELECT 'acceso', true, ST_MakeLine(p.geom, punto.geom)
            FROM (SELECT id, ST_Transform(geom, 32719) AS geom FROM nodos_clave) p
            CROSS JOIN LATERAL (
                SELECT e.geom FROM (
                    SELECT ST_StartPoint(r.geom) AS geom FROM red r
                    UNION ALL SELECT ST_EndPoint(r.geom) FROM red r
                ) e
                ORDER BY e.geom <-> p.geom LIMIT 1
            ) punto
            WHERE ST_Distance(p.geom, punto.geom) > %s
            RETURNING id
            """,
            (TOLERANCIA,),
        )
        n = cur.rowcount
    conn.commit()
    return n


def asignar_vertices(conn):
    """Guarda en nodos_clave el vértice de la topología que representa a cada nodo."""
    with conn.cursor() as cur:
        cur.execute("ALTER TABLE nodos_clave ADD COLUMN IF NOT EXISTS vertice bigint")
        cur.execute(
            """UPDATE nodos_clave n SET vertice = (
                   SELECT v.id FROM red_vertices_pgr v
                   ORDER BY v.the_geom <-> ST_Transform(n.geom, 32719) LIMIT 1)"""
        )
    conn.commit()


def componentes_nodos_clave(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT c.component, array_agg(n.nombre ORDER BY n.id)
            FROM nodos_clave n
            JOIN pgr_connectedComponents(
                'SELECT id, source, target, cost, reverse_cost FROM red') c
              ON c.node = n.vertice
            GROUP BY c.component
            ORDER BY count(*) DESC
            """
        )
        return cur.fetchall()


def agregar_puente(conn, comp_a, comp_b):
    """Une con un tramo recto el par de vértices más cercano entre dos componentes."""
    with conn.cursor() as cur:
        cur.execute(
            """
            WITH c AS (SELECT * FROM pgr_connectedComponents(
                         'SELECT id, source, target, cost, reverse_cost FROM red')),
                 a AS (SELECT v.* FROM red_vertices_pgr v JOIN c ON c.node = v.id
                       WHERE c.component = %s),
                 b AS (SELECT v.* FROM red_vertices_pgr v JOIN c ON c.node = v.id
                       WHERE c.component = %s)
            INSERT INTO red (capa, sintetico, geom)
            SELECT 'puente', true, ST_MakeLine(a.the_geom, cerca.the_geom)
            FROM a CROSS JOIN LATERAL (
                SELECT b.the_geom FROM b ORDER BY b.the_geom <-> a.the_geom LIMIT 1) cerca
            ORDER BY ST_Distance(a.the_geom, cerca.the_geom) LIMIT 1
            RETURNING id, round(ST_Length(geom)), ST_AsText(ST_Transform(ST_Centroid(geom), 4326))
            """,
            (comp_a, comp_b),
        )
        fila = cur.fetchone()
    conn.commit()
    return fila


def reporte(conn):
    with conn.cursor() as cur:
        print("\nEnlaces por capa:")
        cur.execute(
            """SELECT capa, sintetico, count(*), round(sum(largo_m)/1000)
               FROM red GROUP BY 1, 2 ORDER BY sintetico, 3 DESC"""
        )
        print(f"  {'capa':<11}{'sintético':<11}{'enlaces':>8}{'km':>9}")
        for capa, sint, n, km in cur.fetchall():
            print(f"  {capa:<11}{'sí' if sint else 'no':<11}{n:>8}{km:>9,.0f}")

        cur.execute("SELECT count(*) FROM red_vertices_pgr")
        nv = cur.fetchone()[0]
        cur.execute(
            """SELECT count(DISTINCT component),
                      max(n), sum(CASE WHEN n <= 2 THEN 1 ELSE 0 END)
               FROM (SELECT component, count(*) n FROM pgr_connectedComponents(
                       'SELECT id, source, target, cost, reverse_cost FROM red')
                     GROUP BY component) t"""
        )
        ncomp, mayor, chicas = cur.fetchone()
        cur.execute(
            """SELECT count(*) FROM (
                   SELECT v FROM (SELECT source v FROM red UNION ALL SELECT target FROM red) x
                   GROUP BY v HAVING count(*) = 1) d"""
        )
        colgantes = cur.fetchone()[0]
        cur.execute("SELECT count(*), min(prob_falla), max(prob_falla) FROM red")
        ne, pmin, pmax = cur.fetchone()

        # Limitación de los datos: conectividad usando solo la fibra detectada
        cur.execute(
            """WITH c AS (SELECT * FROM pgr_connectedComponents(
                   'SELECT id, source, target, cost, reverse_cost FROM red WHERE capa = ''fibra'''))
               SELECT (SELECT count(DISTINCT component) FROM c),
                      count(DISTINCT c.component)
               FROM nodos_clave n
               CROSS JOIN LATERAL (
                   SELECT c.component FROM c JOIN red_vertices_pgr v ON v.id = c.node
                   ORDER BY v.the_geom <-> ST_Transform(n.geom, 32719) LIMIT 1) c"""
        )
        comp_fibra, comp_fibra_nodos = cur.fetchone()

    print(f"\nVértices (red_vertices_pgr): {nv}")
    print(f"Enlaces (red): {ne}   prob_falla en [{pmin}, {pmax}]")
    print(f"Componentes conexas: {ncomp}  (mayor: {mayor} vértices; "
          f"{chicas} componentes de 1-2 vértices)")
    print(f"Vértices colgantes (grado 1): {colgantes}")
    print(f"Solo con fibra detectada: {comp_fibra} componentes; los 17 nodos clave "
          f"quedarían repartidos en {comp_fibra_nodos} de ellas")


def main():
    conn = conectar()
    print("1) Unión de capas + pgr_nodeNetwork + tabla red")
    ejecutar_sql(conn, "01_topologia.sql")
    notices(conn)

    print(f"2) Enlaces sintéticos de acceso a nodos clave: {agregar_accesos(conn)}")

    print(f"3) pgr_createTopology('red', {TOLERANCIA}, 'geom', 'id')")
    print("   ->", crear_topologia(conn))
    notices(conn)
    asignar_vertices(conn)

    print("4) Conectividad de los nodos clave")
    while True:
        comps = componentes_nodos_clave(conn)
        for comp, nombres in comps:
            print(f"   componente {comp}: {', '.join(nombres)}")
        if len(comps) == 1:
            break
        id_, largo, centro = agregar_puente(conn, comps[0][0], comps[1][0])
        print(f"   + enlace sintético 'puente' id={id_} ({largo} m, en {centro})")
        crear_topologia(conn)
        conn.notices.clear()
        asignar_vertices(conn)

    reporte(conn)
    conn.close()


if __name__ == "__main__":
    main()
