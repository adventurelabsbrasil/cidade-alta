"""Árvores a partir do mapa de altura de copa (Meta/WRI, CC-BY 4.0).

O OSM não tem nenhuma árvore no anel 1 (decisão 009). O mapa de copa da Meta/WRI
estima, a ~1 m por pixel, a altura da vegetação a partir de imagem de satélite.
Cada célula da grade com copa vira uma árvore low-poly com a altura medida: tronco + copa de cor chapada. Ficam de fora as que caem na pista ou
dentro de um prédio. Sorteio de cor e forma por hash: reprodutível (decisão 003).

A janela do tile é lida por HTTP do bucket público e guardada em
data/chm/raw/<tile>.tif; rodar de novo usa o arquivo local.
"""

from __future__ import annotations

import hashlib
import math

import numpy as np
import rasterio
import shapely
import trimesh
from pyproj import Transformer
from rasterio.windows import from_bounds

CHM_URL = "/vsicurl/https://dataforgood-fb-data.s3.amazonaws.com/forests/v1/alsgedi_global_v6_float/chm/{quadkey}.tif"
CORES_COPA = [(74, 112, 58, 255), (92, 128, 64, 255), (60, 96, 54, 255), (104, 136, 70, 255)]
COR_TRONCO = (96, 74, 56, 255)


def quadkey(lat: float, lon: float, z: int = 9) -> str:
    """Tile do mapa de copa: os arquivos são nomeados pelo quadkey de zoom 9."""
    n = 2 ** z
    x = int((lon + 180) / 360 * n)
    y = int((1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n)
    return "".join(str(((x >> i) & 1) + 2 * ((y >> i) & 1)) for i in range(z - 1, -1, -1))


def ler_copa(cfg: dict, frame, half: float, cache):
    """Janela do mapa de copa que cobre o tile, em EPSG:3857 (altura em metros, uint8)."""
    if not cache.exists():
        lons, lats = frame.geo([-half - 20, half + 20], [-half - 20, half + 20])
        to_merc = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
        x0, y0 = to_merc.transform(min(lons), min(lats))
        x1, y1 = to_merc.transform(max(lons), max(lats))
        with rasterio.open(CHM_URL.format(quadkey=quadkey(cfg["center_lat"], cfg["center_lon"]))) as src:
            win = from_bounds(x0, y0, x1, y1, src.transform).round_offsets().round_lengths()
            data = src.read(1, window=win)
            prof = src.profile | {"height": data.shape[0], "width": data.shape[1],
                                  "transform": src.window_transform(win), "tiled": True,
                                  "blockxsize": 256, "blockysize": 256, "compress": "deflate"}
        cache.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(cache, "w", **prof) as dst:
            dst.write(data, 1)
    with rasterio.open(cache) as src:
        return src.read(1).astype(np.float64), src.transform


def topos(chm: np.ndarray, transform, frame, altura_min: float, celula_m: float, fracao_min: float):
    """Uma árvore por célula com copa: (x, y, altura) no referencial do tile.

    Pico local só acha uma árvore por mancha e a mata contínua some (cobria 6% da
    copa medida). A grade preenche a mancha: célula de `celula_m` com pelo menos
    `fracao_min` de copa ganha uma árvore no pixel mais alto dela.
    """
    px = abs(transform.a)
    n = max(1, round(celula_m / px))
    rows, cols = chm.shape[0] // n, chm.shape[1] // n
    blocos = chm[:rows * n, :cols * n].reshape(rows, n, cols, n).transpose(0, 2, 1, 3).reshape(rows, cols, n * n)
    fracao = (blocos >= altura_min).mean(axis=2)
    alto = blocos.argmax(axis=2)
    r, c = np.nonzero(fracao >= fracao_min)
    pr = r * n + alto[r, c] // n
    pc = c * n + alto[r, c] % n
    mx, my = rasterio.transform.xy(transform, pr, pc)
    to_geo = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
    lon, lat = to_geo.transform(np.asarray(mx), np.asarray(my))
    x, y = frame.local(lon, lat)
    return np.column_stack([x, y, chm[pr, pc]])


def gerar(cfg: dict, frame, terrain, half: float, lines, sources, scene, build) -> None:
    import build_tile as bt  # helpers do pipeline (import tardio, como em aparencia.py)

    ac = cfg["arvores"]
    chm, transform = ler_copa(cfg, frame, half, build / f"../chm/raw/{cfg['name']}.tif")
    celula = ac.get("celula_m", 8.0)
    pts = topos(chm, transform, frame, ac.get("altura_min_m", 3.0), celula, ac.get("fracao_min", 0.5))

    # Fora da pista (com folga de calçada) e fora dos prédios.
    pista = shapely.union_all([ln.buffer(bt.road_width(p) / 2 + 1.5) for ln, p in lines])
    predios = shapely.union_all([g for _, g in sources])
    livre = shapely.box(-half, -half, half, half).difference(pista).difference(predios)
    shapely.prepare(livre)
    dentro = shapely.contains_xy(livre, pts[:, 0], pts[:, 1])
    pts = pts[dentro]

    troncos, copas = [], []
    zs = terrain.height(pts[:, 0], pts[:, 1])
    for (x, y, h), z in zip(pts, zs):
        h = min(h, ac.get("altura_max_m", 22.0))
        seed = f"arvore:{x:.1f}:{y:.1f}"
        k = int(hashlib.md5(seed.encode()).hexdigest()[:8], 16)
        r = float(np.clip(0.45 * h, 2.0, celula * 0.65))
        fuste = h * 0.3
        t = trimesh.creation.cylinder(radius=0.12 + 0.012 * h, height=fuste, sections=5)
        t.apply_translation([x, y, z + fuste / 2])
        c = trimesh.creation.icosphere(subdivisions=0, radius=1.0)
        c.apply_scale([r, r, (h - fuste) / 2 * 1.05])
        c.apply_transform(trimesh.transformations.rotation_matrix((k % 360) * math.pi / 180, [0, 0, 1]))
        c.apply_translation([x, y, z + fuste + (h - fuste) / 2])
        for m, cor, lista in ((t, COR_TRONCO, troncos), (c, CORES_COPA[k % len(CORES_COPA)], copas)):
            m.vertices = bt.to_godot(m.vertices)
            m.visual = trimesh.visual.ColorVisuals(m, face_colors=np.tile(cor, (len(m.faces), 1)))
            lista.append(m)

    # Tronco colide (o carro não atravessa árvore); copa não.
    if troncos:
        scene.add_geometry(trimesh.util.concatenate(troncos), node_name="arvores_troncos-col", geom_name="arvores_troncos")
        scene.add_geometry(trimesh.util.concatenate(copas), node_name="arvores_copas", geom_name="arvores_copas")
    print(f"árvores: {len(troncos)} (de {int(dentro.size)} células com copa; o resto caía na pista ou em prédio)")
