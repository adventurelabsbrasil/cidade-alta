"""Ticket #12 — mede candidatos a pontos de descoberta por anel (decisão 008).

Lê data/build/aneis.geojsonseq (osmium export de aneis.osm.pbf), classifica por
categoria, deduplica, mede distância à via dirigível mais próxima e conta por anel.
Sem dependências (projeção equiretangular local; erro < 0,1% em 5 km).

Uso: python3 pipeline/medir_pontos.py data/build/aneis.geojsonseq [saida.json]
"""
from __future__ import annotations

import json
import math
import sys
import unicodedata
from collections import defaultdict

CENTER = (-50.5243758, -29.8305702)  # Pátio Urbano (pipeline/medir_aneis.py)
RINGS_M = [2100, 3500, 5000]  # decisão 008
DRIVABLE = {
    "motorway", "trunk", "primary", "secondary", "tertiary", "unclassified",
    "residential", "living_street", "service", "road", "track",
    "motorway_link", "trunk_link", "primary_link", "secondary_link", "tertiary_link",
}
KX = 111320.0 * math.cos(math.radians(CENTER[1]))
KY = 110574.0


def xy(lon, lat):
    return ((lon - CENTER[0]) * KX, (lat - CENTER[1]) * KY)


def ring_of(d):
    for i, r in enumerate(RINGS_M):
        if d <= r:
            return i
    return None


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return " ".join(s.split())


def poly_centroid(ring):
    a = cx = cy = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        c = x1 * y2 - x2 * y1
        a += c; cx += (x1 + x2) * c; cy += (y1 + y2) * c
    if abs(a) < 1e-9:
        n = len(ring)
        return (sum(p[0] for p in ring) / n, sum(p[1] for p in ring) / n)
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


def seg_dist(p, a, b):
    ax, ay = a; bx, by = b; px, py = p
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def seg_intersect(a, b, c, d):
    def o(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    return o(a, b, c) * o(a, b, d) <= 0 and o(c, d, a) * o(c, d, b) <= 0


PUBLIC = {"townhall", "courthouse", "fire_station", "police", "hospital", "clinic",
          "community_centre", "library", "bus_station", "post_office", "social_facility",
          "arts_centre", "theatre", "prison"}


def category(p):
    if p.get("leisure") in ("park", "common", "garden"):
        return "parque/praça"
    if p.get("amenity") == "place_of_worship" or p.get("building") in ("church", "chapel", "cathedral"):
        return "igreja"
    if p.get("amenity") in ("school", "university", "college", "kindergarten"):
        return "escola/universidade"
    if p.get("tourism") in ("viewpoint", "attraction", "museum") or "historic" in p:
        return "mirante/atração"
    if p.get("amenity") in PUBLIC or p.get("office") == "government":
        return "prédio público"
    # candidatos extras (fora da lista do ticket), medidos para comparação
    if p.get("man_made") in ("water_tower", "tower"):
        return "extra: torre/caixa d'água"
    if p.get("amenity") == "fuel":
        return "extra: posto"
    if p.get("shop") in ("mall", "supermarket", "department_store"):
        return "extra: mercado/shopping"
    if p.get("leisure") in ("pitch", "stadium", "sports_centre"):
        return "extra: campo/estádio"
    if p.get("place") in ("neighbourhood", "suburb", "hamlet", "village", "quarter"):
        return "extra: bairro/localidade"
    if p.get("landuse") == "cemetery":
        return "extra: cemitério"
    if p.get("natural") == "water" and p.get("name"):
        return "extra: lagoa/açude nomeado"
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
            roads.append((p, pts))
        if "waterway" in p:
            waterways.append((p, pts))
    segs = [(a, b) for _, pts in roads for a, b in zip(pts, pts[1:])]

    def road_dist(pt):
        return min(seg_dist(pt, a, b) for a, b in segs)

    def nearest_road_name(pt):
        best = (1e18, None)
        for p, pts in roads:
            if not p.get("name"):
                continue
            for a, b in zip(pts, pts[1:]):
                d = seg_dist(pt, a, b)
                if d < best[0]:
                    best = (d, p["name"])
        return best[1] if best[0] < 40 else None

    cands = []
    for f in feats:
        p, g = f["properties"], f["geometry"]
        cat = category(p)
        if not cat:
            continue
        pt = rep_point(g)
        if pt is None:
            continue
        cands.append({"cat": cat, "name": p.get("name"), "pt": pt, "osm_id": f.get("id"), "geom": g["type"]})

    # pontes: highway dirigível com bridge=*, agrupadas por (via, curso d'água)
    bridges = {}
    for p, pts in roads:
        if p.get("bridge") in (None, "no"):
            continue
        ww = None
        for wp, wpts in waterways:
            if any(seg_intersect(a, b, c, d) for a, b in zip(pts, pts[1:]) for c, d in zip(wpts, wpts[1:])):
                ww = wp.get("name") or f"sem nome ({wp.get('waterway')})"
                break
        mid = pts[len(pts) // 2]
        key = (norm(p.get("name")) or f"@{round(mid[0], -2)},{round(mid[1], -2)}", ww or "sem curso d'água no OSM")
        bridges.setdefault(key, {"cat": "ponte", "name": p.get("name") and f"Ponte {p['name']} / {key[1]}",
                                 "pt": mid, "geom": "LineString", "ways": 0})["ways"] += 1
    cands += list(bridges.values())

    # travessias: via dirigível x curso d'água NOMEADO (com ou sem bridge=*), por (via, curso)
    cross = {}
    for p, pts in roads:
        for wp, wpts in waterways:
            if not wp.get("name") or wp.get("waterway") not in ("river", "stream", "canal"):
                continue
            for a, b in zip(pts, pts[1:]):
                hit = next(((c, d) for c, d in zip(wpts, wpts[1:]) if seg_intersect(a, b, c, d)), None)
                if hit:
                    key = (norm(p.get("name")) or f"@{round(a[0], -2)},{round(a[1], -2)}", wp["name"])
                    cross.setdefault(key, {"cat": "extra: travessia de arroio nomeado",
                                           "name": f"{wp['name']} ({p.get('name') or 'via sem nome'})",
                                           "pt": a, "geom": "LineString"})
                    break
    cands += list(cross.values())

    # rotatórias / trevos: junction=roundabout|circular agrupadas a 80 m
    rbs = []
    for p, pts in roads:
        if p.get("junction") in ("roundabout", "circular"):
            c = (sum(x for x, _ in pts) / len(pts), sum(y for _, y in pts) / len(pts))
            for r in rbs:
                if math.dist(r["pt"], c) < 80:
                    break
            else:
                rbs.append({"cat": "rotatória/trevo", "name": p.get("name"), "pt": c, "geom": "LineString"})
    for f in feats:
        if f["properties"].get("highway") == "motorway_junction":
            rbs.append({"cat": "rotatória/trevo", "name": f["properties"].get("name"), "pt": xy(*f["geometry"]["coordinates"]), "geom": "Point"})
    for r in rbs:
        if not r["name"]:
            n = nearest_road_name(r["pt"])
            r["name_derivado"] = n and f"Rotatória da {n}"
    cands += rbs

    # dedup: mesma categoria + mesmo nome a <150 m, ou sem nome a <50 m (nó+área)
    kept = []
    for c in sorted(cands, key=lambda c: (c["geom"] == "Point",)):  # prefere área
        dup = False
        for k in kept:
            if k["cat"] != c["cat"]:
                continue
            d = math.dist(k["pt"], c["pt"])
            if (c["name"] and norm(c["name"]) == norm(k["name"]) and d < 400) or (d < 50 and (not c["name"] or not k["name"])):
                dup = True
                k["name"] = k["name"] or c["name"]
                break
        if not dup:
            kept.append(c)

    kept = [c for c in kept if not (c["cat"] == "mirante/atração" and any(
        k is not c and k["name"] and c["name"] and norm(c["name"]) in norm(k["name"]) and math.dist(k["pt"], c["pt"]) < 100 for k in kept))]
    for c in kept:
        c["dist_centro"] = math.hypot(*c["pt"])
        c["anel"] = ring_of(c["dist_centro"])
        c["dist_via"] = road_dist(c["pt"])
    kept = [c for c in kept if c["anel"] is not None]

    table = defaultdict(lambda: [[0, 0] for _ in RINGS_M])  # [nomeados, sem nome]
    for c in kept:
        table[c["cat"]][c["anel"]][0 if c["name"] else 1] += 1
    print(f"{'categoria':32} " + " | ".join(f"anel{i+1} nom/sem" for i in range(3)))
    for cat in sorted(table):
        print(f"{cat:32} " + " | ".join(f"{n:>5}/{s:<5}  " for n, s in table[cat]))

    print("\nDetalhe (anel, cat, nome, dist_via m):")
    for c in sorted(kept, key=lambda c: (c["anel"], c["cat"], c["dist_centro"])):
        print(f"  {c['anel']+1} {c['cat']:28} {str(c['name'] or c.get('name_derivado') or '-')[:60]:60} centro={c['dist_centro']:6.0f} via={c['dist_via']:5.0f}")
    named = defaultdict(lambda: [set(), set()])
    for p, pts in roads:
        if p.get("name"):
            r = ring_of(math.hypot(*pts[len(pts) // 2]))
            if r is not None:
                named[r][0 if p["highway"] in ("primary", "secondary", "tertiary", "trunk") else 1].add(norm(p["name"]))
    for r in range(3):
        print(f"vias nomeadas anel{r+1}: arteriais={len(named[r][0])} locais={len(named[r][1] - named[r][0])}")
    if out:
        json.dump([{k: v for k, v in c.items()} for c in kept], open(out, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
