"""Modelo de falla: atenuación de PGA (Youngs et al., 1997) + fragilidad HAZUS (Tabla 8-30)."""
import math

# Youngs et al. (1997), roca, sismo de interfaz (Zt = 0). PGA en g.
A1, A2, A4, A5, A6 = 0.2418, 1.414, 1.7818, 0.554, 0.00607
C1, C2, C3, C4, C5 = 0.0, 0.0, -2.552, 1.45, -0.1

# HAZUS 4.2, Tabla 8-30, circuitos de distribución sin anclaje / estándar:
# (estado de daño, mediana PGA [g], beta, fracción de circuitos que falla)
FRAGILIDAD = [
    ("leve",      0.24, 0.25, 0.04),
    ("moderado",  0.33, 0.20, 0.12),
    ("extensivo", 0.58, 0.15, 0.50),
    ("completo",  0.89, 0.15, 0.80),
]


def sigma_pga(mag):
    return C4 + C5 * min(mag, 8.0)


def pga(dist_epi_km, mag, prof_km):
    """Mediana de PGA (g) a una distancia epicentral dada; R = distancia hipocentral."""
    r = math.hypot(dist_epi_km, prof_km)
    ln_y = (A1 + A2 * mag + C1 + C2 * (10 - mag) ** 3
            + C3 * math.log(r + A4 * math.exp(A5 * mag)) + A6 * prof_km)
    return math.exp(ln_y)


def phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def prob_estados(pga_g, sigma):
    """P(DS >= ds) para cada estado, combinando la dispersión de la fragilidad y de la PGA."""
    return [phi(math.log(pga_g / med) / math.hypot(beta, sigma))
            for _, med, beta, _ in FRAGILIDAD]


def prob_falla(dist_epi_km, mag, prof_km):
    """Probabilidad de falla de un enlace = fracción esperada de circuitos que fallan."""
    excede = prob_estados(pga(dist_epi_km, mag, prof_km), sigma_pga(mag)) + [0.0]
    return sum(f * (excede[i] - excede[i + 1]) for i, (_, _, _, f) in enumerate(FRAGILIDAD))


if __name__ == "__main__":
    MAG, PROF = 8.8, 22.9
    print(f"Mw {MAG}, profundidad {PROF} km, sigma ln(PGA) = {sigma_pga(MAG):.2f}\n")
    print(f"{'d_epi (km)':>10}{'PGA (g)':>9}{'P(>=leve)':>11}{'P(>=mod)':>10}"
          f"{'P(>=ext)':>10}{'P(>=comp)':>11}{'P falla':>9}")
    for d in [0, 25, 50, 75, 100, 150, 200, 300, 400, 500]:
        a = pga(d, MAG, PROF)
        e = prob_estados(a, sigma_pga(MAG))
        print(f"{d:>10}{a:>9.3f}" + "".join(f"{x:>10.4f}" for x in e)
              + f"{prob_falla(d, MAG, PROF):>10.4f}")
