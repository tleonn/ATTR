from db import conectar, ejecutar_sql
from modelo_falla import prob_falla as prob_falla_py

UMBRALES = [0.0001, 0.001, 0.01, 0.05, 0.1]


def resumen(cur):
    cur.execute(
        """SELECT count(*), count(*) FILTER (WHERE prob_falla > 0.0001),
                  min(prob_falla), avg(prob_falla), max(prob_falla),
                  sum(prob_falla * largo_m) / 1000
           FROM red"""
    )
    n, afectados, pmin, pmed, pmax, km_esperados = cur.fetchone()
    print(f"Enlaces: {n}  |  con p > 0,0001: {afectados}")
    print(f"p mín = {pmin:.2e}  p media = {pmed:.4f}  p máx = {pmax:.4f}")
    print(f"Km de red que se espera fallen (Σ p·largo): {km_esperados:,.0f} km")

    print("\nDistribución de enlaces por probabilidad de falla:")
    limites = [0] + UMBRALES + [1]
    for lo, hi in zip(limites, limites[1:]):
        cur.execute(
            "SELECT count(*), coalesce(sum(largo_m), 0) / 1000 FROM red "
            "WHERE prob_falla > %s AND prob_falla <= %s", (lo, hi))
        c, km = cur.fetchone()
        print(f"  ({lo:<6} - {hi:<6}]  {c:>5} enlaces  {km:>8,.0f} km")

    print("\nPor capa:")
    cur.execute(
        """SELECT capa, count(*), count(*) FILTER (WHERE prob_falla > 0.01),
                  avg(prob_falla), max(prob_falla)
           FROM red GROUP BY capa ORDER BY max(prob_falla) DESC"""
    )
    print(f"  {'capa':<11}{'enlaces':>8}{'p>0,01':>8}{'p media':>10}{'p máx':>9}")
    for capa, c, c1, pm, px in cur.fetchall():
        print(f"  {capa:<11}{c:>8}{c1:>8}{pm:>10.4f}{px:>9.4f}")


def extremos(cur, orden, titulo, filtro="true"):
    cur.execute(
        f"""SELECT r.id, r.capa, r.sintetico, round(r.largo_m) AS largo,
                   r.dist_epicentro_km, r.pga_g, r.prob_falla, cerca.nombre,
                   ST_Y(ST_Transform(ST_Centroid(r.geom), 4326)),
                   ST_X(ST_Transform(ST_Centroid(r.geom), 4326))
            FROM red r
            CROSS JOIN LATERAL (
                SELECT nombre FROM nodos_clave n
                ORDER BY n.geom::geography <-> ST_Transform(ST_Centroid(r.geom), 4326)::geography
                LIMIT 1) cerca
            WHERE {filtro}
            ORDER BY r.prob_falla {orden}, r.dist_epicentro_km {'ASC' if orden == 'DESC' else 'DESC'}, r.id
            LIMIT 10"""
    )
    print(f"\n{titulo}")
    print(f"  {'id':>5} {'capa':<10}{'largo m':>8}{'d epi km':>9}{'PGA g':>7}{'p falla':>10}"
          f"  {'nodo clave más cercano':<24}{'lat, lon'}")
    for id_, capa, sint, largo, d, pga, p, nodo, lat, lon in cur.fetchall():
        print(f"  {id_:>5} {capa + ('*' if sint else ''):<10}{largo:>8.0f}{d:>9.1f}{pga:>7.3f}"
              f"{p:>10.2e}  {nodo:<24}{lat:.3f}, {lon:.3f}")


def verificar(cur):
    """Compara la función SQL con la implementación Python del modelo."""
    cur.execute("SELECT magnitud, profundidad_km FROM sismo")
    mag, prof = cur.fetchone()
    cur.execute("SELECT dist_epicentro_km, prob_falla FROM red ORDER BY random() LIMIT 200")
    error = max(abs(p - prob_falla_py(d, mag, prof)) for d, p in cur.fetchall())
    print(f"\nVerificación SQL vs Python (200 enlaces): error máximo = {error:.1e}")


def main():
    conn = conectar()
    ejecutar_sql(conn, "02_prob_falla.sql")
    with conn.cursor() as cur:
        resumen(cur)
        extremos(cur, "DESC", "Enlaces MÁS afectados (* = sintético):")
        extremos(cur, "DESC", "Enlaces de FIBRA (reales) más afectados:", "NOT r.sintetico")
        extremos(cur, "ASC", "Enlaces MENOS afectados (* = sintético):")
        verificar(cur)
    conn.close()


if __name__ == "__main__":
    main()
