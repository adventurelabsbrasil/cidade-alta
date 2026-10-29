# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "numpy",
#   "scipy",
#   "rasterio",
#   "pyproj",
#   "shapely>=2.1",
#   "trimesh",
#   "overturemaps",
#   "mapbox-earcut",
# ]
# ///
"""Gera um tile da cidade (terreno + ruas + prédios) em glTF, a partir de dado real.

Pipeline da decisão 003: osmium sobre o extract da Geofabrik, prédios do Overture,
relevo do Copernicus GLO-30, ruas por shapely + trimesh. Reprodutível: rodar de novo
sobre um extract mais novo gera o tile atualizado, sem edição manual.

Uso:
    uv run pipeline/build_tile.py pipeline/tiles/fatia.toml
"""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
import tomllib
from pathlib import Path

import numpy as np
import rasterio
import shapely
import trimesh
from pyproj import Transformer
from rasterio.windows import from_bounds
from scipy.ndimage import gaussian_filter, map_coordinates
from shapely.geometry import box, shape

ROOT = Path(__file__).resolve().parent.parent
OSM_PBF = ROOT / "data/osm/raw/sul-latest.osm.pbf"
DEM_TIF = ROOT / "data/dem/raw/cop30_S30_W051.tif"
BUILD = ROOT / "data/build"
OUT = ROOT / "game/world/tiles"

# SIRGAS 2000 / UTM 22S: métrico, cobre Santo Antônio da Patrulha.
UTM = "EPSG:31982"

DRIVABLE = {
    "motorway", "trunk", "primary", "secondary", "tertiary", "unclassified",
    "residential", "living_street", "service", "road", "track",
    "motorway_link", "trunk_link", "primary_link", "secondary_link", "tertiary_link",
}
# Largura padrão por classe, em metros, quando a via não tem `width` nem `lanes`.
WIDTH_BY_CLASS = {
    "motorway": 12.0, "trunk": 10.0, "primary": 9.0, "secondary": 8.0,
    "tertiary": 7.0, "unclassified": 6.0, "residential": 6.0, "living_street": 5.0,
    "road": 6.0, "service": 4.0, "track": 3.5,
}
LANE_WIDTH = 3.2

# Paleta única de cores chapadas (decisão 001). RGBA 0-255.
PALETTE = {
    "terrain": (122, 150, 92, 255),
    "road": (64, 66, 72, 255),
    "unpaved": (150, 120, 88, 255),
    "buildings": [
        (232, 222, 200, 255), (214, 196, 170, 255), (240, 236, 228, 255),
        (196, 170, 150, 255), (226, 208, 160, 255), (190, 200, 196, 255),
    ],
}
UNPAVED = {"unpaved", "dirt", "gravel", "ground", "sand", "compacted", "fine_gravel"}

ROAD_LIFT = 0.12  # a pista fica um pouco acima do terreno, sem z-fighting
ROAD_CELL = 6.0   # célula de recorte das ruas: cada pedaço segue o relevo
FLOOR_H = 3.0


def load_config(path: Path) -> dict:
    with path.open("rb") as f:
        return tomllib.load(f)


class Frame:
    """Referencial local do tile: x = leste, y = norte, em metros a partir do centro."""

    def __init__(self, lat: float, lon: float):
        self.to_utm = Transformer.from_crs("EPSG:4326", UTM, always_xy=True)
        self.to_geo = Transformer.from_crs(UTM, "EPSG:4326", always_xy=True)
        self.ox, self.oy = self.to_utm.transform(lon, lat)

    def local(self, lon, lat):
        x, y = self.to_utm.transform(lon, lat)
        return np.asarray(x) - self.ox, np.asarray(y) - self.oy

    def geo(self, x, y):
        return self.to_geo.transform(np.asarray(x) + self.ox, np.asarray(y) + self.oy)

    def localize(self, geom):
        return shapely.transform(geom, lambda c: np.column_stack(self.local(c[:, 0], c[:, 1])))


class Terrain:
    """Altura suavizada do DEM, amostrada bilinear em coordenadas locais."""

    def __init__(self, frame: Frame, half: float, sigma: float):
        self.frame = frame
        lons, lats = frame.geo([-half - 200, half + 200], [-half - 200, half + 200])
        with rasterio.open(DEM_TIF) as src:
            win = from_bounds(min(lons), min(lats), max(lons), max(lats), src.transform)
            win = win.round_offsets().round_lengths()
            self.data = gaussian_filter(src.read(1, window=win).astype(np.float64), sigma)
            self.inv = ~src.window_transform(win)
        self.base = 0.0
        self.base = float(self.height(np.array([0.0]), np.array([0.0]))[0])

    def height(self, x, y):
        lon, lat = self.frame.geo(x, y)
        col, row = self.inv * (np.asarray(lon), np.asarray(lat))
        # O pixel do GeoTIFF é endereçado pelo canto; o centro fica em +0,5.
        z = map_coordinates(self.data, [np.asarray(row) - 0.5, np.asarray(col) - 0.5], order=1, mode="nearest")
        return z - self.base


def osm_features(cfg: dict, half: float, frame: Frame) -> list[dict]:
    """Recorta o extract pelo bbox do tile (com margem) e exporta GeoJSON."""
    BUILD.mkdir(parents=True, exist_ok=True)
    lons, lats = frame.geo([-half - 150, half + 150], [-half - 150, half + 150])
    bbox = f"{min(lons)},{min(lats)},{max(lons)},{max(lats)}"
    pbf = BUILD / f"{cfg['name']}.osm.pbf"
    geojson = BUILD / f"{cfg['name']}.geojsonseq"
    subprocess.run(["osmium", "extract", "-s", "smart", "-b", bbox, str(OSM_PBF), "-o", str(pbf), "--overwrite"], check=True)
    subprocess.run(["osmium", "export", str(pbf), "-f", "geojsonseq", "-o", str(geojson), "--overwrite"], check=True)
    feats = []
    for line in geojson.read_text().splitlines():
        line = line.strip("\x1e").strip()
        if line:
            feats.append(json.loads(line))
    return feats


def road_width(props: dict) -> float:
    try:
        return float(str(props["width"]).replace(",", ".").split()[0])
    except (KeyError, ValueError):
        pass
    try:
        return int(props["lanes"]) * LANE_WIDTH
    except (KeyError, ValueError):
        return WIDTH_BY_CLASS.get(props.get("highway"), 6.0)


def triangulate(poly, terrain: Terrain, lift: float):
    """Triangula um polígono e põe cada vértice na altura do relevo."""
    tris = shapely.constrained_delaunay_triangles(poly)
    verts, faces = [], []
    for tri in shapely.get_parts(tris):
        coords = np.asarray(tri.exterior.coords)[:3]
        base = len(verts)
        verts.extend(coords)
        faces.append((base, base + 1, base + 2))
    if not verts:
        return None
    v = np.asarray(verts)
    z = terrain.height(v[:, 0], v[:, 1]) + lift
    return np.column_stack([v[:, 0], v[:, 1], z]), np.asarray(faces)


def to_godot(verts: np.ndarray) -> np.ndarray:
    """(leste, norte, cima) -> glTF/Godot (x, y cima, -z norte)."""
    return np.column_stack([verts[:, 0], verts[:, 2], -verts[:, 1]])


def colored(verts, faces, rgba, name):
    m = trimesh.Trimesh(vertices=to_godot(verts), faces=faces, process=True)
    # Superfície de altura: toda face aponta pra cima (+Y no Godot), pra colisão e luz.
    down = m.face_normals[:, 1] < 0
    m.faces[down] = m.faces[down][:, ::-1]
    m.visual = trimesh.visual.ColorVisuals(m, face_colors=np.tile(rgba, (len(m.faces), 1)))
    m.metadata["name"] = name
    return m


def build_terrain(terrain: Terrain, half: float, step: float):
    n = int(round(2 * half / step)) + 1
    xs = np.linspace(-half, half, n)
    gx, gy = np.meshgrid(xs, xs)
    z = terrain.height(gx.ravel(), gy.ravel())
    verts = np.column_stack([gx.ravel(), gy.ravel(), z])
    i = np.arange(n - 1)
    a = (i[:, None] * n + i[None, :]).ravel()
    faces = np.concatenate([
        np.column_stack([a, a + 1, a + n + 1]),
        np.column_stack([a, a + n + 1, a + n]),
    ])
    return verts, faces


def build_roads(feats, frame: Frame, terrain: Terrain, half: float):
    tile = box(-half, -half, half, half)
    paved, unpaved, lines = [], [], []
    for f in feats:
        p = f["properties"]
        if p.get("highway") not in DRIVABLE or f["geometry"]["type"] != "LineString":
            continue
        line = frame.localize(shape(f["geometry"]))
        lines.append((line, p))
        poly = line.buffer(road_width(p) / 2, cap_style="round", join_style="round", quad_segs=4)
        (unpaved if p.get("surface") in UNPAVED else paved).append(poly)
    out = {}
    for key, polys in (("paved", paved), ("unpaved", unpaved)):
        if not polys:
            continue
        area = shapely.union_all(polys).intersection(tile)
        if key == "unpaved" and paved:
            area = area.difference(shapely.union_all(paved))
        # Recorta em células pequenas pra que cada triângulo acompanhe o relevo.
        n = int(math.ceil(2 * half / ROAD_CELL))
        cells = [box(-half + i * ROAD_CELL, -half + j * ROAD_CELL, -half + (i + 1) * ROAD_CELL, -half + (j + 1) * ROAD_CELL)
                 for i in range(n) for j in range(n)]
        cells = np.asarray(cells, dtype=object)
        cells = cells[shapely.intersects(cells, area)]
        pieces = shapely.intersection(cells, area)
        verts, faces = [], []
        for piece in pieces:
            for part in shapely.get_parts(piece):
                if part.geom_type != "Polygon" or part.area < 0.01:
                    continue
                r = triangulate(part, terrain, ROAD_LIFT)
                if r is None:
                    continue
                faces.append(r[1] + sum(len(v) for v in verts))
                verts.append(r[0])
        if verts:
            out[key] = (np.concatenate(verts), np.concatenate(faces))
    return out, lines


def overture_buildings(name: str, frame: Frame, half: float) -> list[dict]:
    lons, lats = frame.geo([-half, half], [-half, half])
    out = BUILD / f"{name}_overture.geojson"
    bbox = f"{min(lons)},{min(lats)},{max(lons)},{max(lats)}"
    cli = Path(sys.executable).parent / "overturemaps"
    cmd = [str(cli), "download", f"--bbox={bbox}", "-f", "geojson", "--type=building", "-o", str(out)]
    try:
        subprocess.run(cmd, check=True, timeout=600)
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        print(f"aviso: Overture indisponível ({e}); usando só o OSM", file=sys.stderr)
        return []
    return json.loads(out.read_text()).get("features", [])


def building_height(props: dict, area: float, seed: str) -> float:
    """Altura do dado quando existe; senão heurística por área (decisão 001)."""
    for key in ("height",):
        try:
            h = float(props[key])
            if h > 0:
                return h
        except (KeyError, TypeError, ValueError):
            pass
    for key in ("num_floors", "building:levels"):
        try:
            return max(1, int(float(props[key]))) * FLOOR_H
        except (KeyError, TypeError, ValueError):
            pass
    r = int(hashlib.md5(seed.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    floors = 1 if area < 120 else 2 if area < 400 else 3
    return floors * FLOOR_H + r * 1.5 + 0.5


def build_buildings(sources, frame: Frame, terrain: Terrain, half: float):
    tile = box(-half, -half, half, half)
    meshes = []
    for i, (props, geom) in enumerate(sources):
        poly = frame.localize(geom)
        if not poly.within(tile):
            continue
        for part in shapely.get_parts(poly):
            if part.geom_type != "Polygon" or part.area < 8:
                continue
            ring = np.asarray(part.exterior.coords)
            ground = terrain.height(ring[:, 0], ring[:, 1])
            h = building_height(props, part.area, f"{i}:{part.centroid.wkt}")
            # A base desce até o ponto mais baixo do terreno: sem prédio flutuando na encosta.
            m = trimesh.creation.extrude_polygon(part, h + (ground.max() - ground.min()) + 0.5, engine="earcut")
            m.apply_translation([0, 0, ground.min() - 0.5])
            color = PALETTE["buildings"][int(hashlib.md5(str(i).encode()).hexdigest(), 16) % len(PALETTE["buildings"])]
            m.vertices = to_godot(m.vertices)  # rotação própria: a orientação das faces se mantém
            m.visual = trimesh.visual.ColorVisuals(m, face_colors=np.tile(color, (len(m.faces), 1)))
            meshes.append(m)
    if not meshes:
        return None
    merged = trimesh.util.concatenate(meshes)
    merged.metadata["name"] = "predios"
    return merged, len(meshes)


def spawn_point(lines, terrain: Terrain, street: str):
    """Ponto médio do trecho mais longo da via de spawn, apontando no sentido do traçado."""
    cands = [ln for ln, p in lines if street.lower() in (p.get("name") or "").lower()]
    if not cands:
        return None
    ln = max(cands, key=lambda g: g.length)
    a = ln.interpolate(0.5, normalized=True)
    b = ln.interpolate(min(1.0, 0.5 + 10 / ln.length), normalized=True)
    z = float(terrain.height(np.array([a.x]), np.array([a.y]))[0])
    heading = math.atan2(b.x - a.x, b.y - a.y)  # radianos a partir do norte, sentido horário
    return {"x": a.x, "y": z + 1.5, "z": -a.y, "heading_from_north": heading}


def main() -> None:
    cfg = load_config(Path(sys.argv[1]))
    half = cfg["size_m"] / 2
    frame = Frame(cfg["center_lat"], cfg["center_lon"])
    terrain = Terrain(frame, half, cfg["dem_sigma_px"])

    feats = osm_features(cfg, half, frame)
    scene = trimesh.Scene()

    tv, tf = build_terrain(terrain, half, cfg["terrain_step_m"])
    scene.add_geometry(colored(tv, tf, PALETTE["terrain"], "terreno"), node_name="terreno-col", geom_name="terreno")

    roads, lines = build_roads(feats, frame, terrain, half)
    for key, (v, f) in roads.items():
        color = PALETTE["road"] if key == "paved" else PALETTE["unpaved"]
        scene.add_geometry(colored(v, f, color, key), node_name=f"ruas_{key}-col", geom_name=f"ruas_{key}")

    overture = overture_buildings(cfg["name"], frame, half)
    if overture:
        sources = [(f["properties"], shape(f["geometry"])) for f in overture]
        source_name = "overture"
    else:
        sources = [(f["properties"], shape(f["geometry"])) for f in feats
                   if "building" in f["properties"] and f["geometry"]["type"] in ("Polygon", "MultiPolygon")]
        source_name = "osm"
    built = build_buildings(sources, frame, terrain, half)
    if built:
        scene.add_geometry(built[0], node_name="predios-col", geom_name="predios")

    OUT.mkdir(parents=True, exist_ok=True)
    glb = OUT / f"{cfg['name']}.glb"
    scene.export(glb)

    osm_buildings = sum(1 for f in feats if "building" in f["properties"])
    meta = {
        "name": cfg["name"],
        "center": {"lat": cfg["center_lat"], "lon": cfg["center_lon"]},
        "size_m": cfg["size_m"],
        "base_altitude_m": round(terrain.base, 1),
        "spawn": spawn_point(lines, terrain, cfg["spawn_street"]),
        "stats": {
            "roads_drivable": len(lines),
            "buildings": built[1] if built else 0,
            "buildings_source": source_name,
            "buildings_osm_in_extract": osm_buildings,
            "buildings_overture_in_bbox": len(overture),
            "terrain_relief_m": round(float(tv[:, 2].max() - tv[:, 2].min()), 1),
            "triangles": int(sum(len(g.faces) for g in scene.geometry.values())),
        },
    }
    (OUT / f"{cfg['name']}.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(meta, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
