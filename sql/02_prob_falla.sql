-- Modelo de falla (docs/sismo_modelo_falla.md):
--   PGA: Youngs et al. (1997), roca, interfaz
--   Fragilidad: HAZUS 4.2, Tabla 8-30, circuitos de distribución sin anclaje

CREATE OR REPLACE FUNCTION pga_youngs(dist_epi_km double precision,
                                      mag double precision,
                                      prof_km double precision)
RETURNS double precision LANGUAGE sql IMMUTABLE AS $$
    SELECT exp(0.2418 + 1.414 * mag
               - 2.552 * ln(sqrt(dist_epi_km ^ 2 + prof_km ^ 2) + 1.7818 * exp(0.554 * mag))
               + 0.00607 * prof_km)
$$;

CREATE OR REPLACE FUNCTION fragilidad(pga_g double precision, mediana double precision,
                                      beta double precision, sigma double precision)
RETURNS double precision LANGUAGE sql IMMUTABLE AS $$
    SELECT 0.5 * (1 + erf(ln(pga_g / mediana) / sqrt(beta ^ 2 + sigma ^ 2) / sqrt(2)))
$$;

CREATE OR REPLACE FUNCTION prob_falla_sismo(dist_epi_km double precision,
                                            mag double precision,
                                            prof_km double precision)
RETURNS double precision LANGUAGE sql IMMUTABLE AS $$
    WITH a AS (SELECT pga_youngs(dist_epi_km, mag, prof_km) AS pga,
                      1.45 - 0.1 * least(mag, 8) AS sigma),
         p AS (SELECT fragilidad(pga, 0.24, 0.25, sigma) AS leve,
                      fragilidad(pga, 0.33, 0.20, sigma) AS moderado,
                      fragilidad(pga, 0.58, 0.15, sigma) AS extensivo,
                      fragilidad(pga, 0.89, 0.15, sigma) AS completo
               FROM a)
    SELECT 0.04 * (leve - moderado) + 0.12 * (moderado - extensivo)
         + 0.50 * (extensivo - completo) + 0.80 * completo
    FROM p
$$;

ALTER TABLE red ADD COLUMN IF NOT EXISTS dist_epicentro_km double precision;
ALTER TABLE red ADD COLUMN IF NOT EXISTS pga_g double precision;

UPDATE red r
SET dist_epicentro_km = ST_Distance(r.geom, ST_Transform(s.geom, 32719)) / 1000,
    pga_g             = pga_youngs(ST_Distance(r.geom, ST_Transform(s.geom, 32719)) / 1000,
                                   s.magnitud, s.profundidad_km),
    prob_falla        = prob_falla_sismo(ST_Distance(r.geom, ST_Transform(s.geom, 32719)) / 1000,
                                         s.magnitud, s.profundidad_km)
FROM sismo s
WHERE s.id = 'official20100227063411530_30';
