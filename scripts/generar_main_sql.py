import os
import re
import subprocess

from db import ROOT, conectar

EXCLUIR = ["red_base", "red_base_noded", "red_base_noded_id_seq", "attr_resultado", "attr_par"]
OMITIR = ("--", "SET ", "SELECT pg_catalog.set_config")
TABLAS = ["fibra_optica", "postacion_electrica", "camino_sin_postacion", "trayecto_ferry",
          "nodos_clave", "sismo", "red", "red_vertices_pgr"]


def ordenar_tablas():
    conn = conectar()
    conn.autocommit = True
    with conn.cursor() as cur:
        for t in TABLAS:
            cur.execute(f"CLUSTER {t} USING {t}_pkey")
    conn.close()


def generar(destino=ROOT / "main.sql"):
    ordenar_tablas()
    cmd = ["docker", "compose", "exec", "-T", "db", "pg_dump",
           "-U", os.getenv("DB_USER", "postgres"), "-d", os.getenv("DB_NAME", "attr"),
           "--no-owner", "--no-privileges", "--no-comments", "--rows-per-insert=500"]
    for t in EXCLUIR:
        cmd += ["-T", t]
    volcado = subprocess.run(cmd, cwd=ROOT, check=True, capture_output=True, text=True).stdout
    lineas = [l for l in volcado.splitlines() if not l.startswith(OMITIR)]
    texto = re.sub(r"\n{3,}", "\n\n", "\n".join(lineas)).strip() + "\n"
    destino.write_text(texto, encoding="utf-8")
    return destino


def resumen(conn):
    with conn.cursor() as cur:
        cur.execute(
            """SELECT (SELECT count(*) FROM red), (SELECT count(*) FROM red_vertices_pgr),
                      (SELECT count(*) FROM nodos_clave), (SELECT count(*) FROM sismo),
                      (SELECT count(*) FROM red WHERE prob_falla > 0),
                      (SELECT round(sum(prob_falla)::numeric, 6) FROM red)"""
        )
        return cur.fetchone()


def main():
    destino = generar()
    print(f"{destino.name}: {destino.stat().st_size / 1e6:.1f} MB")
    conn = conectar()
    red, vert, nodos, sismo, con_p, suma_p = resumen(conn)
    conn.close()
    print(f"  red: {red} enlaces ({con_p} con prob_falla > 0, Σ p = {suma_p})")
    print(f"  red_vertices_pgr: {vert}  nodos_clave: {nodos}  sismo: {sismo}")


if __name__ == "__main__":
    main()
