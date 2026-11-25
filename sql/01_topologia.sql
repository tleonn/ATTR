-- =====================================================================
-- Topología de red a partir de la infraestructura del Estudio
--   * fibra_optica                         -> enlaces reales (sintetico = false)
--   * postacion_electrica, camino_sin_postacion, trayecto_ferry
--                                          -> enlaces sintéticos (sintetico = true):
--     rutas físicas documentadas por el Estudio en las que no se detectó
--     fibra, pero que el propio Estudio usa para construir su grafo (p. 39).
-- Se trabaja en EPSG:32719 (WGS84 / UTM 19S) para que la tolerancia
-- quede expresada en metros.
-- =====================================================================

DROP TABLE IF EXISTS red_base, red_base_noded, red, red_vertices_pgr CASCADE;

-- 1) Unión de las capas en una sola tabla de tramos
CREATE TABLE red_base AS
SELECT row_number() OVER (ORDER BY orden, gid)::bigint AS id, capa, sintetico,
       ST_Transform(geom, 32719)    AS geom
FROM (
    SELECT 1 AS orden, gid, 'fibra'     AS capa, false AS sintetico, geom FROM fibra_optica
    UNION ALL SELECT 2, gid, 'postacion', true, geom FROM postacion_electrica
    UNION ALL SELECT 3, gid, 'camino',    true, geom FROM camino_sin_postacion
    UNION ALL SELECT 4, gid, 'ferry',     true, geom FROM trayecto_ferry
) u;

-- 2) Nodado: corta los tramos en las uniones en "T" (un tramo que termina
--    en el interior de otro), que pgr_createTopology no detecta porque solo
--    une extremos. Misma tolerancia que la topología.
SELECT pgr_nodeNetwork('red_base', 10, 'id', 'geom');

-- 3) Tabla de enlaces definitiva
CREATE TABLE red (
    id           bigserial PRIMARY KEY,
    id_base      bigint,                    -- tramo original en red_base
    capa         text    NOT NULL,          -- fibra / postacion / camino / ferry / acceso / puente
    sintetico    boolean NOT NULL,
    geom         geometry(LineString, 32719),
    source       bigint,
    target       bigint,
    largo_m      double precision,
    cost         double precision,
    reverse_cost double precision,
    prob_falla   double precision NOT NULL DEFAULT 0   -- 0 = infraestructura en operación
);

INSERT INTO red (id_base, capa, sintetico, geom)
SELECT n.old_id, b.capa, b.sintetico, n.geom
FROM red_base_noded n
JOIN red_base b ON b.id = n.old_id
WHERE ST_Length(n.geom) > 0
ORDER BY n.old_id, n.sub_id;
