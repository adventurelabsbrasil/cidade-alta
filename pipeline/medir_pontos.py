"""Mede candidatos a pontos de descoberta por anel (decisões 008, 010 e 011).

Uso: python3 pipeline/medir_pontos.py data/build/aneis.geojsonseq [saida.json]
"""
from __future__ import annotations

import json
import math
import sys
import unicodedata
from collections import defaultdict

CENTER = (-50.5243758, -29.8305702)  # Pátio Urbano
RINGS_M = [2100, 3500, 5000]
DRIVABLE = {
    "motorway", "trunk", "primary", "secondary", "tertiary", "unclassified",
    "residential", "living_street", "service", "road", "track",
    "motorway_link", "trunk_link", "primary_link", "secondary_link", "tertiary_link",
}
KX = 111320.0 * math.cos(math.radians(CENTER[1]))
KY = 110574.0
PUBLIC = {"townhall", "courthouse", "fire_station", "police", "hospital", "clinic",
          "community_centre", "library", "bus_station", "post_office", "social_facility",
          "arts_centre", "theatre", "prison"}


def xy(lon, lat):
    return ((lon - CENTER[0]) * KX, (lat - CENTER[1]) * KY)


def lonlat(pt):
    return (CENTER[0] + pt[0] / KX, CENTER[1] + pt[1] / KY)


def ring_of(d):
    for i, r in enumerate(RINGS_M):
        if d <= r:
            return i
    return None


def norm(s):
    return " ".join(unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower().split())


def poly_centroid(ring):
    a = cx = cy = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        c = x1 * y2 - x2 * y1
        a += c; cx += (x1 + x2) * c; cy += (y1 + y2) * c
    if abs(a) < 1e-9:
        return (sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring))
    return (cx / (3 * a), cy / (3 * a))


def rep_point(geom):
    t, c = geom["type"], geom["coordinates"]
    if t == "Point":
        return xy(*c)
    if t == "LineString":
        pts = [xy(*p) for p in c]
        return pts[len(pts) // 2]
    if t == "Polygon":
        return poly_centroid([xy(*p) for p in c[0]])
    if t == "MultiPolygon":
        big = max(c, key=lambda p: len(p[0]))
        return poly_centroid([xy(*p) for p in big[0]])
    return None


def nearest_on_seg(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = dx * dx + dy * dy
    t = 0 if length == 0 else max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / length))
    q = (a[0] + t * dx, a[1] + t * dy)
    return q, math.dist(p, q)


def seg_intersect(a, b, c, d):
    def orient(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    return orient(a, b, c) * orient(a, b, d) <= 0 and orient(c, d, a) * orient(c, d, b) <= 0


def category(p):
    if p.get("leisure") in ("park", "common", "garden"):
        return "parque/praça"
    if p.get("amenity") == "place_of_worship" or p.get("building") in ("church", "chapel", "cathedral"):
        return "igreja"
    if p.get("amenity") in ("school", "university", "college", "kindergarten"):
        return "escola/universidade"
    if p.get("tourism") in ("viewpoint", "attraction"):
        return "mirante/atração"
    if p.get("amenity") in PUBLIC or p.get("office") == "government":
        return "prédio público"
    if p.get("place") in ("neighbourhood", "suburb", "hamlet", "village", "quarter"):
        return "bairro"
    return None


def main(path, out=None):
    feats = []
    for line in open(path, encoding="utf-8"):
        line = line.strip("\x1e").strip()
        if line:
            feats.append(json.loads(line))

    roads, waterways = [], []
    for f in feats:
        p, g = f["properties"], f["geometry"]
        if g["type"] != "LineString":
            continue
        pts = [xy(*c) for c in g["coordinates"]]
        if p.get("highway") in DRIVABLE:
            roads.append((p, pts, f.get("id")))
        if "waterway" in p:
            waterways.append((p, pts))
    segs = [(a, b) for _, pts, _ in roads for a, b in zip(pts, pts[1:])]

    def nearest_road(pt):
        return min((nearest_on_seg(pt, a, b)[1], nearest_on_seg(pt, a, b)[0]) for a, b in segs)

    def road_name(pt):
        named = []
        for p, pts, _ in roads:
            if not p.get("name"):
                continue
            for a, b in zip(pts, pts[1:]):
                named.append((nearest_on_seg(pt, a, b)[1], p["name"]))
        return min(named)[1] if named and min(named)[0] <= 40 else None

    cands = []
    for f in feats:
        p, g = f["properties"], f["geometry"]
        cat, pt = category(p), rep_point(g)
        if cat and pt is not None:
            cands.append({"cat": cat, "name": p.get("name"), "pt": pt, "osm_id": f.get("id"), "geom": g["type"]})

    bridges = {}
    for p, pts, osm_id in roads:
        if p.get("bridge") in (None, "no"):
            continue
        ww = None
        for wp, wpts in waterways:
            if any(seg_intersect(a, b, c, d) for a, b in zip(pts, pts[1:]) for c, d in zip(wpts, wpts[1:])):
                ww = wp.get("name") or f"sem nome ({wp.get('waterway')})"
                break
        mid = pts[len(pts) // 2]
        name = p.get("name") or road_name(mid)
        key = (norm(name) or f"@{round(mid[0], -2)},{round(mid[1], -2)}", ww or "sem curso d'água no OSM")
        bridges.setdefault(key, {"cat": "ponte", "name": name and f"Ponte {name}", "pt": mid,
                                 "osm_id": osm_id, "geom": "LineString"})
    cands += list(bridges.values())

    rbs = []
    for p, pts, osm_id in roads:
        if p.get("junction") not in ("roundabout", "circular"):
            continue
        c = (sum(x for x, _ in pts) / len(pts), sum(y for _, y in pts) / len(pts))
        if not any(math.dist(r["pt"], c) < 80 for r in rbs):
            name = p.get("name") or road_name(c)
            rbs.append({"cat": "rotatória", "name": name and f"Rotatória da {name}", "pt": c,
                        "osm_id": osm_id, "geom": "LineString"})
    for f in feats:
        p, g = f["properties"], f["geometry"]
        if p.get("highway") == "motorway_junction" and g["type"] == "Point":
            pt = xy(*g["coordinates"])
            name = p.get("name") or road_name(pt)
            if name:
                rbs.append({"cat": "rotatória", "name": f"Rotatória da {name}", "pt": pt,
                            "osm_id": f.get("id"), "geom": "Point"})
    cands += rbs

    kept = []
    for c in sorted(cands, key=lambda c: (c["geom"] == "Point",)):
        generic = norm(c["name"]).startswith("area verde") or norm(c["name"]) == "quadra esportiva publica"
        if not c["name"] or generic:
            continue
        if any(k["cat"] == c["cat"] and norm(k["name"]) == norm(c["name"]) and math.dist(k["pt"], c["pt"]) < 400 for k in kept):
            continue
        kept.append(c)

    for c in kept:
        c["dist_centro"] = math.hypot(*c["pt"])
        c["anel"] = ring_of(c["dist_centro"])
        c["dist_via"], c["trigger"] = nearest_road(c["pt"])
        if c["cat"] == "bairro":
            c["pt"] = c["trigger"]
    kept = [c for c in kept if c["anel"] is not None and c["dist_via"] <= (250 if c["cat"] == "bairro" else 60)]

    specs = [
        ("landmark:patio-urbano", "Pátio Urbano", "centro", CENTER, None),
        ("landmark:igreja-boa-viagem", "Igreja N. Sra. da Boa Viagem", "igreja", None, ("boa viagem",)),
        ("landmark:igreja-matriz", "Igreja Matriz", "igreja", None, ("paroquia santo antonio",)),
        ("landmark:fonte-imperial", "Fonte Imperial", "mirante/atração", None, ("praca da fonte imperial", "fonte imperial")),
        ("landmark:rodoviaria", "Rodoviária", "prédio público", None, ("rodoviaria",)),
    ]
    landmarks = []
    for lid, name, cat, fixed, aliases in specs:
        match = None if fixed else next((c for c in kept if any(alias in norm(c["name"]) for alias in aliases)), None)
        pt = xy(*fixed) if fixed else match["pt"] if match else None
        if pt is None:
            print(f"aviso: landmark sem ponto OSM: {name}", file=sys.stderr)
            continue
        if match:
            # o landmark substitui só o ponto do mesmo lugar; vizinhos seguem (decisão 010)
            kept = [c for c in kept if not any(alias in norm(c["name"]) for alias in aliases)]
        landmarks.append({"id": lid, "nome": name, "categoria": cat, "pt": pt, "peso": 2,
                          "landmark": True, "anel": ring_of(math.hypot(*pt))})

    points = []
    for c in kept:
        lon, lat = lonlat(c["pt"])
        points.append({"id": c["osm_id"], "osm_id": c["osm_id"], "nome": c["name"], "categoria": c["cat"],
                       "lon": lon, "lat": lat, "x": c["pt"][0], "y": c["pt"][1], "peso": 1,
                       "landmark": False, "anel": c["anel"] + 1})
    for c in landmarks:
        lon, lat = lonlat(c["pt"])
        points.append({"id": c["id"], "nome": c["nome"], "categoria": c["categoria"], "lon": lon, "lat": lat,
                       "x": c["pt"][0], "y": c["pt"][1], "peso": c["peso"], "landmark": True, "anel": c["anel"] + 1})

    table = defaultdict(lambda: [[0, 0] for _ in RINGS_M])
    for c in kept:
        table[c["cat"]][c["anel"]][0] += 1
    print(f"{'categoria':32} " + " | ".join(f"anel{i+1} nom/sem" for i in range(3)))
    for cat in sorted(table):
        print(f"{cat:32} " + " | ".join(f"{n:>5}/{s:<5}  " for n, s in table[cat]))
    print("\nResumo pontos finais:")
    for i in range(3):
        ring_points = [p for p in points if p["anel"] == i + 1]
        total = sum(p["peso"] for p in ring_points)
        print(f"  anel{i+1}: {len(ring_points)} pontos, peso {total}, limiar {max(math.ceil(0.6 * total), 10)}")
    print("\nDetalhe (anel, cat, nome, dist_via m):")
    for c in sorted(kept, key=lambda c: (c["anel"], c["cat"], c["dist_centro"])):
        print(f"  {c['anel']+1} {c['cat']:28} {c['name'][:60]:60} centro={c['dist_centro']:6.0f} via={c['dist_via']:5.0f}")
    if out:
        ring_points = [p for p in points if p["anel"] == 1]
        total = sum(p["peso"] for p in ring_points)
        json.dump({"pontos": ring_points, "resumo": {"anel": 1, "pontos": len(ring_points),
                   "peso_total": total, "limiar": max(math.ceil(0.6 * total), 10)}},
                  open(out, "w"), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
