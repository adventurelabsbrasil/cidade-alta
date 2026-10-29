"""Aparência por regra: aplica uma regra de `pipeline/regras/` aos prédios e à
rua em volta de uma via (piloto da Rua 15 de Novembro, #16).

A regra descreve o padrão da rua (tipologias, paleta, telhado, frente do lote,
pavimento, postes). Aqui ela vira geometria low-poly com cor chapada por vértice
(decisão 001). Todo sorteio usa hash do índice e da posição: rodar de novo gera
o mesmo resultado (decisão 003).
"""

from __future__ import annotations

import hashlib
import math
import tomllib
from pathlib import Path

import numpy as np
import shapely
import trimesh
from shapely.geometry import Point, box
from shapely.ops import substring

REGRAS = Path(__file__).resolve().parent / "regras"
WALL_PIECE = 4.0  # o muro é feito em pedaços que acompanham o relevo


def rgba(hexcolor: str) -> tuple[int, int, int, int]:
    h = hexcolor.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255


def sorteio(seed: str) -> float:
    return int(hashlib.md5(seed.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


def escolhe(seq, seed: str):
    return seq[int(sorteio(seed) * len(seq)) % len(seq)]


def volume(mesh: trimesh.Trimesh, color, to_godot) -> trimesh.Trimesh:
    mesh.vertices = to_godot(mesh.vertices)
    mesh.visual = trimesh.visual.ColorVisuals(mesh, face_colors=np.tile(color, (len(mesh.faces), 1)))
    return mesh


def telhado(part, top: float, cfg: dict):
    """Duas águas sobre o retângulo mínimo da pegada, cumeeira no lado comprido."""
    rect = part.minimum_rotated_rectangle.buffer(cfg["beiral_m"], join_style="mitre")
    c = np.asarray(rect.exterior.coords)[:4]
    if np.linalg.norm(c[1] - c[0]) < np.linalg.norm(c[2] - c[1]):
        c = np.roll(c, -1, axis=0)  # c0-c1 e c2-c3 passam a ser os lados compridos
    r1, r2 = (c[3] + c[0]) / 2, (c[1] + c[2]) / 2
    short = np.linalg.norm(c[1] - c[2])
    rise = short / 2 * math.tan(math.radians(cfg["inclinacao_graus"]))
    v = np.array([[*c[0], top], [*c[1], top], [*c[2], top], [*c[3], top], [*r1, top + rise], [*r2, top + rise]])
    faces = np.array([[0, 1, 5], [0, 5, 4], [2, 3, 4], [2, 4, 5], [1, 2, 5], [3, 0, 4]])
    # Normal pra fora: compara com o centro da base do telhado.
    center = np.array([*rect.centroid.coords[0], top])
    for i, f in enumerate(faces):
        n = np.cross(v[f[1]] - v[f[0]], v[f[2]] - v[f[0]])
        if np.dot(n, v[f].mean(axis=0) - center) < 0:
            faces[i] = f[::-1]
    return trimesh.Trimesh(vertices=v, faces=faces, process=False)


def muro(part, eixo, offset: float, terrain, cfg: dict):
    """Muro na divisa do lote com a calçada, do comprimento da frente do prédio."""
    ln = min(shapely.get_parts(eixo), key=lambda g: g.distance(part))
    ring = np.asarray(part.exterior.coords)
    s = [ln.project(Point(p)) for p in ring]
    seg = substring(ln, max(0.0, min(s) - 1.0), min(ln.length, max(s) + 1.0))
    if seg.length < 2.0:
        return []
    sides = [seg.offset_curve(d) for d in (offset, -offset)]
    side = min(sides, key=lambda g: g.distance(part.centroid))
    if side.is_empty or side.geom_type != "LineString" or side.buffer(0.1).intersects(part):
        return []
    pieces = []
    n = max(1, int(math.ceil(side.length / WALL_PIECE)))
    for i in range(n):
        piece = substring(side, i * side.length / n, (i + 1) * side.length / n)
        poly = piece.buffer(0.08, cap_style="flat")
        if poly.is_empty or poly.geom_type != "Polygon":
            continue
        c = np.asarray(poly.exterior.coords)
        g = terrain.height(c[:, 0], c[:, 1])
        m = trimesh.creation.extrude_polygon(poly, cfg["muro_altura_m"] + (g.max() - g.min()) + 0.3, engine="earcut")
        m.apply_translation([0, 0, g.min() - 0.3])
        pieces.append(m)
    return pieces


def aplicar(regra: dict, sources, lines, frame, terrain, half: float, scene):
    """Gera a rua e os prédios da regra e devolve as fontes que sobraram."""
    import build_tile as bt  # helpers do pipeline (import tardio: build_tile importa este módulo)

    with (REGRAS / f"{regra['regra']}.toml").open("rb") as f:
        cfg = tomllib.load(f)
    tile = box(-half, -half, half, half)
    rua = [(ln, p) for ln, p in lines if p.get("name") == regra["rua"]]
    if not rua:
        print(f"aviso: via {regra['rua']!r} não está no tile; regra ignorada")
        return sources
    eixo = shapely.union_all([ln for ln, _ in rua])
    w = max(bt.road_width(p) for _, p in rua)
    calcada = cfg["rua"]["calcada_m"]

    # Pavimento e calçada. A calçada não cobre as vias que cruzam.
    pista = shapely.union_all([ln.buffer(w / 2, cap_style="flat", quad_segs=4) for ln, _ in rua]).intersection(tile)
    outras = shapely.union_all([ln.buffer(bt.road_width(p) / 2) for ln, p in lines if p.get("name") != regra["rua"]])
    passeio = eixo.buffer(w / 2 + calcada, cap_style="flat").difference(pista).difference(outras).intersection(tile)
    for nome, area, lift, cor in (
        ("ruas_pedra", pista, bt.ROAD_LIFT, cfg["rua"]["pavimento"]),
        ("calcada", passeio, bt.ROAD_LIFT + cfg["rua"]["meio_fio_m"], cfg["rua"]["calcada_cor"]),
    ):
        mesh = bt.mesh_area(area, terrain, half, lift)
        if mesh:
            scene.add_geometry(bt.colored(*mesh, rgba(cor), nome), node_name=f"{nome}-col", geom_name=nome)

    # Prédios a até raio_m do eixo.
    corpos, telhados, muros, resto = [], [], [], []
    tip, fachada, frente = cfg["tipologia"], cfg["fachada"], cfg["frente"]
    for i, (props, geom) in enumerate(sources):
        poly = frame.localize(geom)
        if not poly.within(tile) or poly.centroid.distance(eixo) > regra["raio_m"]:
            resto.append((props, geom))
            continue
        for j, part in enumerate(shapely.get_parts(poly)):
            if part.geom_type != "Polygon" or part.area < 8:
                continue
            seed = f"{regra['regra']}:{i}:{j}"
            ring = np.asarray(part.exterior.coords)
            ground = terrain.height(ring[:, 0], ring[:, 1])
            sobrado = part.area >= tip["sobrado_min_m2"] and sorteio(seed + ":tipo") < tip["sobrado_peso"]
            h = (2 if sobrado else 1) * tip["pe_direito_m"] + sorteio(seed + ":h") * 0.4
            m = trimesh.creation.extrude_polygon(part, h + (ground.max() - ground.min()) + 0.5, engine="earcut")
            m.apply_translation([0, 0, ground.min() - 0.5])
            corpos.append(volume(m, rgba(escolhe(fachada["cores"], seed + ":cor")), bt.to_godot))
            roof = telhado(part, ground.max() + h, cfg["telhado"])
            telhados.append(volume(roof, rgba(escolhe(cfg["telhado"]["cores"], seed + ":telha")), bt.to_godot))
            recuo = part.distance(eixo) - (w / 2 + calcada)
            if recuo > frente["recuo_muro_m"]:
                cor = rgba(escolhe(frente["muro_cores"], seed + ":muro"))
                muros += [volume(p, cor, bt.to_godot) for p in muro(part, eixo, w / 2 + calcada + 0.2, terrain, frente)]

    # Postes de um lado da rua e fiação entre eles.
    postes, fios = [], []
    pc = cfg["postes"]
    for ln, _ in rua:
        side = ln.offset_curve(w / 2 + 0.4)
        if side.is_empty or side.geom_type != "LineString":
            continue
        tops = []
        for d in np.arange(pc["espacamento_m"] / 2, side.length, pc["espacamento_m"]):
            pt = side.interpolate(d)
            if not tile.contains(pt):
                continue
            z = float(terrain.height(np.array([pt.x]), np.array([pt.y]))[0])
            m = trimesh.creation.cylinder(radius=0.13, height=pc["altura_m"], sections=6)
            m.apply_translation([pt.x, pt.y, z + pc["altura_m"] / 2])
            postes.append(volume(m, rgba(pc["cor"]), bt.to_godot))
            tops.append([pt.x, pt.y, z + pc["altura_m"] - 0.6])
        for a, b in zip(tops, tops[1:]):
            m = trimesh.creation.cylinder(radius=0.02, segment=[a, b], sections=4)
            fios.append(volume(m, rgba(pc["fio_cor"]), bt.to_godot))

    for nome, meshes, col in (("predios_regra", corpos, True), ("telhados", telhados, False),
                              ("muros", muros, True), ("postes", postes, True), ("fios", fios, False)):
        if meshes:
            merged = trimesh.util.concatenate(meshes)
            scene.add_geometry(merged, node_name=f"{nome}-col" if col else nome, geom_name=nome)
    print(f"aparência {regra['regra']!r} em {regra['rua']!r}: {len(corpos)} prédios, "
          f"{len(muros)} pedaços de muro, {len(postes)} postes")
    return resto
