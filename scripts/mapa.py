import json

import folium
from branca.element import Element

from db import ROOT

CLASES = [
    (0.001, "#86b6ef", 1.5, "≤ 0,001"),
    (0.01, "#5598e7", 2.0, "0,001 – 0,01"),
    (0.05, "#2a78d6", 2.5, "0,01 – 0,05"),
    (0.1, "#1c5cab", 3.5, "0,05 – 0,1"),
    (1.0, "#0d366b", 4.5, "> 0,1"),
]
RADIOS_KM = [50, 100, 150, 300]
IZQUIERDA = {"Valparaíso", "Concepción"}
GRIS = ("https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/"
        "MapServer/tile/{z}/{y}/{x}")


def clase(p):
    return next(c for c in CLASES if p <= c[0])


def enlaces(cur, sinteticos):
    cur.execute(
        """SELECT id, capa, prob_falla, largo_m, dist_epicentro_km, pga_g,
                  ST_AsGeoJSON(ST_Transform(ST_SimplifyPreserveTopology(geom, 20), 4326), 5)
           FROM red WHERE sintetico = %s ORDER BY prob_falla""",
        (sinteticos,),
    )
    return {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "geometry": json.loads(g),
             "properties": {"id": i, "capa": capa, "p": round(p, 5), "largo_km": round(l / 1000, 2),
                            "dist_km": round(d, 1), "pga_g": round(a, 3)}}
            for i, capa, p, l, d, a, g in cur.fetchall()
        ],
    }


def capa_enlaces(datos, nombre, punteado):
    def estilo(f):
        _, color, peso, _ = clase(f["properties"]["p"])
        return {"color": color, "weight": peso, "opacity": 0.9 if not punteado else 0.75,
                "dashArray": "4 4" if punteado else None}

    grupo = folium.FeatureGroup(name=nombre)
    folium.GeoJson(
        datos, style_function=estilo,
        highlight_function=lambda f: {"weight": 6, "color": "#eb6834"},
        tooltip=folium.GeoJsonTooltip(
            fields=["id", "capa", "p", "dist_km", "pga_g", "largo_km"],
            aliases=["Enlace", "Capa", "P falla", "Dist. epicentro (km)", "PGA (g)", "Largo (km)"]),
    ).add_to(grupo)
    return grupo


def capa_nodos(cur):
    cur.execute(
        """WITH p AS (SELECT escenario, nodo_a AS nodo, confiabilidad FROM attr_par
                      UNION ALL SELECT escenario, nodo_b, confiabilidad FROM attr_par)
           SELECT n.nombre, n.tipo, n.rol, ST_Y(n.geom), ST_X(n.geom),
                  avg(p.confiabilidad) FILTER (WHERE p.escenario = 'operacion'),
                  avg(p.confiabilidad) FILTER (WHERE p.escenario = 'terremoto')
           FROM nodos_clave n LEFT JOIN p ON p.nodo = n.nombre
           GROUP BY n.id ORDER BY n.id"""
    )
    grupo = folium.FeatureGroup(name="Nodos clave")
    for nombre, tipo, rol, lat, lon, r0, r1 in cur.fetchall():
        popup = (f"<b>{nombre}</b><br>{tipo}<br>Rol: {rol}<br>"
                 f"R promedio en operación: {r0:.4f}<br>R promedio post 27F: {r1:.4f}")
        folium.CircleMarker(
            [lat, lon], radius=6, color="#ffffff", weight=2, fill=True,
            fill_color="#1f1f1f", fill_opacity=1, popup=folium.Popup(popup, max_width=280),
            tooltip=folium.Tooltip(nombre, permanent=True,
                                   direction="left" if nombre in IZQUIERDA else "right",
                                   class_name="etiqueta-nodo"),
        ).add_to(grupo)
    return grupo


def capa_sismo(cur):
    cur.execute("SELECT id, lugar, magnitud, profundidad_km, fecha_utc, ST_Y(geom), ST_X(geom) FROM sismo")
    id_, lugar, mag, prof, fecha, lat, lon = cur.fetchone()
    grupo = folium.FeatureGroup(name="Epicentro 27F")
    for r in RADIOS_KM:
        folium.Circle([lat, lon], radius=r * 1000, color="#6b6b6b", weight=1, dash_array="2 6",
                      fill=False, tooltip=f"{r} km del epicentro").add_to(grupo)
    folium.Marker(
        [lat, lon], icon=folium.Icon(color="red", icon="star"),
        popup=folium.Popup(f"<b>{lugar}</b><br>Mw {mag} · {prof} km<br>{fecha:%Y-%m-%d %H:%M} UTC"
                           f"<br>USGS {id_}", max_width=260),
        tooltip="Epicentro Mw 8.8",
    ).add_to(grupo)
    return grupo, (lat, lon)


def panel(cur):
    cur.execute("SELECT escenario, attr, ic95 FROM attr_resultado")
    r = {e: (a, ic) for e, a, ic in cur.fetchall()}
    a0, a1, ic = r["operacion"][0], r["terremoto"][0], r["terremoto"][1]
    filas = "".join(
        f'<div class="fila"><span class="muestra" style="background:{c}; height:{w + 1}px"></span>{t}</div>'
        for _, c, w, t in CLASES)
    return f"""
    <style>
      .caja {{position:fixed; z-index:9999; background:#fff; color:#1f1f1f; padding:10px 12px;
              border-radius:8px; box-shadow:0 1px 4px rgba(0,0,0,.25);
              font:12px/1.4 system-ui,-apple-system,sans-serif;}}
      .caja h4 {{margin:0 0 6px; font-size:13px;}}
      .caja .fila {{display:flex; align-items:center; gap:8px; margin:3px 0;}}
      .caja .muestra {{display:inline-block; width:28px; border-radius:2px;}}
      .caja .linea {{display:inline-block; width:28px; border-top:3px solid #2a78d6;}}
      .caja .num {{font-size:20px; font-weight:600;}}
      .caja .sec {{color:#5f5f5f;}}
      .etiqueta-nodo {{background:transparent; border:none; box-shadow:none; font-weight:600;
                       color:#1f1f1f; text-shadow:0 0 3px #fff, 0 0 3px #fff;}}
      .etiqueta-nodo::before {{display:none;}}
    </style>
    <div class="caja" style="top:12px; right:60px; min-width:190px">
      <h4>ATTR entre los 17 nodos clave</h4>
      <div class="sec">En operación</div><div class="num">{a0:.4f}</div>
      <div class="sec">Post terremoto 27F</div><div class="num">{a1:.4f}
        <span class="sec" style="font-size:12px; font-weight:400">± {ic:.4f}</span></div>
      <div class="sec">Diferencia: {a1 - a0:+.4f} ({(a1 - a0) / a0 * 100:+.1f} %)</div>
    </div>
    <div class="caja" style="bottom:44px; left:12px">
      <h4>Probabilidad de falla del enlace</h4>
      {filas}
      <div class="fila" style="margin-top:8px"><span class="linea"></span>Fibra detectada (real)</div>
      <div class="fila"><span class="linea" style="border-top-style:dashed"></span>Enlace sintético</div>
      <div class="fila"><span style="display:inline-block; width:28px; text-align:center">●</span>Nodo clave</div>
      <div class="fila"><span style="display:inline-block; width:28px; text-align:center; color:#d63e2a">★</span>Epicentro (círculos a 50, 100, 150 y 300 km)</div>
    </div>"""


def generar_mapa(conn, destino=ROOT / "output" / "mapa.html", centro=None, zoom=6):
    destino.parent.mkdir(exist_ok=True)
    with conn.cursor() as cur:
        sismo, epicentro = capa_sismo(cur)
        m = folium.Map(location=centro or [epicentro[0] + 1.5, epicentro[1] + 1], zoom_start=zoom,
                       tiles=None, control_scale=True)
        folium.TileLayer(GRIS, name="Mapa base gris (Esri)",
                         attr="Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ").add_to(m)
        folium.TileLayer("OpenStreetMap", name="OpenStreetMap", show=False).add_to(m)
        capa_enlaces(enlaces(cur, True), "Enlaces sintéticos (postación, caminos, ferry, accesos)",
                     True).add_to(m)
        capa_enlaces(enlaces(cur, False), "Fibra detectada (real)", False).add_to(m)
        sismo.add_to(m)
        capa_nodos(cur).add_to(m)
        m.get_root().html.add_child(Element(panel(cur)))
    folium.LayerControl(collapsed=False, position="topleft").add_to(m)
    m.save(str(destino))
    return destino
