import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from attr import attr_exacto, attr_monte_carlo, contraer


def confiabilidad(enlaces, clave, metodo):
    n, c, aleatorios = contraer(enlaces, clave)
    if metodo == "exacto":
        r, _ = attr_exacto(n, c, aleatorios)
    else:
        r, _ = attr_monte_carlo(n, c, aleatorios, 20000, 1)
    return r[0, 1]


def test_serie():
    enlaces = [(1, 2, 0.5), (2, 3, 0.5)]
    esperado = 0.25
    for m in ("exacto", "mc"):
        r = confiabilidad(enlaces, [1, 3], m)
        assert abs(r - esperado) < (1e-12 if m == "exacto" else 0.01), (m, r)
        print(f"serie      {m:<7} {r:.4f}  (teórico {esperado})")


def test_paralelo():
    enlaces = [(1, 2, 0.1), (2, 4, 0.1), (1, 3, 0.1), (3, 4, 0.1)]
    esperado = 1 - (1 - 0.9 ** 2) ** 2
    for m in ("exacto", "mc"):
        r = confiabilidad(enlaces, [1, 4], m)
        assert abs(r - esperado) < (1e-12 if m == "exacto" else 0.01), (m, r)
        print(f"paralelo   {m:<7} {r:.4f}  (teórico {esperado:.4f})")


def test_puente_wheatstone():
    q = 0.2
    enlaces = [(1, 2, q), (1, 3, q), (2, 3, q), (2, 4, q), (3, 4, q)]
    p = 1 - q
    esperado = 2 * p**2 + 2 * p**3 - 5 * p**4 + 2 * p**5
    for m in ("exacto", "mc"):
        r = confiabilidad(enlaces, [1, 4], m)
        assert abs(r - esperado) < (1e-12 if m == "exacto" else 0.01), (m, r)
        print(f"wheatstone {m:<7} {r:.4f}  (teórico {esperado:.4f})")


def test_contraccion():
    enlaces = [(1, 2, 0.0), (2, 3, 0.0), (3, 4, 1.0), (4, 5, 0.0)]
    n, c, aleatorios = contraer(enlaces, [1, 5])
    r, _ = attr_exacto(n, c, aleatorios)
    assert aleatorios == [] and r[0, 1] == 0
    print("contracción: p=0 se fusiona, p=1 se elimina -> R = 0")


if __name__ == "__main__":
    test_serie()
    test_paralelo()
    test_puente_wheatstone()
    test_contraccion()
    print("OK")
