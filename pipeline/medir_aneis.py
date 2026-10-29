# /// script
# requires-python = ">=3.11"
# dependencies = ["pyproj", "shapely>=2.1", "overturemaps"]
# ///
"""Mede os anéis da área jogável (decisão 005): vias e prédios por anel a partir do
centro, e a distância do spawn ao centro.

Uso:
    uv run pipeline/medir_aneis.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import shapely
from pyproj import Transformer
from shapely.geometry import Point, shape

ROOT = Path(__file__).resolve().parent.parent
OSM_PBF = ROOT / "data/osm/raw/sul-latest.osm.pbf"
BUILD = ROOT / "data/build"

# Pátio Urbano (shop=mall no OSM, nó extraído do recorte de 29/10/2026).
CENTER = (-50.5243758, -29.8305702)
RINGS_KM = [1.5, 3.0, 5.0]
DRIVABLE = {
    "motorway", "trunk", "primary", "secondary", "tertiary", "unclassified",
    "residential", "living_street", "service", "road", "track",
    "motorway_link", "trunk_link", "primary_link", "secondary_link", "tertiary_link",
}

to_utm = Transformer.from_crs("EPSG:4326", "EPSG:31982", always_xy=True)
to_geo = Transformer.from_crs("EPSG:31982", "EPSG:4326", always_xy=True)
cx, cy = to_utm.transform(*CENTER)


def local(geom):
    return shapely.transform(geom, lambda c: __import__("numpy").column_stack(to_utm.transform(c[:, 0], c[:, 1])))


def ring_of(dist_m: float) -> int | None:
    for i, r in enumerate(RINGS_KM):
        if dist_m <= r * 1000:
            return i
    return None


def main() -> None:
    BUILD.mkdir(parents=True, exist_ok=True)
    r = RINGS_KM[-1] * 1000 + 200
    lo = to_geo.transform(cx - r, cy - r)
    hi = to_geo.transform(cx + r, cy + r)
    bbox = f"{lo[0]},{lo[1]},{hi[0]},{hi[1]}"
    pbf = BUILD / "aneis.osm.pbf"
    seq = BUILD / "aneis.geojsonseq"
    subprocess.run(["osmium", "extract", "-s", "smart", "-b", bbox, str(OSM_PBF), "-o", str(pbf), "--overwrite"], check=True)
    subprocess.run(["osmium", "export", str(pbf), "-f", "geojsonseq", "-o", str(seq), "--overwrite"], check=True)

    center = Point(cx, cy)
    rings = [{"raio_km": k, "vias": 0, "vias_km": 0.0, "predios_osm": 0, "predios_overture": 0} for k in RINGS_KM]
    spawn = None
    for line in seq.read_text().splitlines():
        line = line.strip("\x1e").strip()
        if not line:
            continue
        f = json.loads(line)
        p = f["properties"]
        g = local(shape(f["geometry"]))
        i = ring_of(g.centroid.distance(center))
        if p.get("highway") in DRIVABLE and f["geometry"]["type"] == "LineString":
            if "Borges de Medeiros" in (p.get("name") or ""):
                d = (g.distance(center), g.hausdorff_distance(center))
                spawn = d if spawn is None else (min(spawn[0], d[0]), max(spawn[1], d[1]))
            if i is not None:
                rings[i]["vias"] += 1
                rings[i]["vias_km"] += g.length / 1000
        elif "building" in p and i is not None:
            rings[i]["predios_osm"] += 1

    cli = Path(sys.executable).parent / "overturemaps"
    ov = BUILD / "aneis_overture.geojson"
    subprocess.run([str(cli), "download", f"--bbox={bbox}", "-f", "geojson", "--type=building", "-o", str(ov)], check=True)
    for f in json.loads(ov.read_text())["features"]:
        i = ring_of(local(shape(f["geometry"])).centroid.distance(center))
        if i is not None:
            rings[i]["predios_overture"] += 1

    for r_ in rings:
        r_["vias_km"] = round(r_["vias_km"], 1)
    print(json.dumps({
        "centro": {"nome": "Pátio Urbano", "lon": CENTER[0], "lat": CENTER[1]},
        "spawn_borges_dist_centro_m": {"min": round(spawn[0]), "max": round(spawn[1])} if spawn else None,
        "aneis": rings,
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
