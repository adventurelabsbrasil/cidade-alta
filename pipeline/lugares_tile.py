# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "pyproj", "shapely>=2.1"]
# ///
"""Lugares feitos à mão (posto, farmácia…) para um tile, a partir de um override.

Lê pipeline/lugares/<tile>.toml e grava game/world/tiles/<tile>.lugares.json com:
- `demolir`: pegadas de prédio a tirar da malha (o prédio que está no lote);
- `pecas`: pisos, caixas e placas, em coordenadas do Godot (x leste, z = -norte).

A altura não vem daqui: o jogo assenta cada peça no terreno do próprio tile. Não
mexe no .glb, então não precisa rodar o build_tile.py de novo.

Uso:
    uv run pipeline/lugares_tile.py pipeline/tiles/anel1.toml
"""

from __future__ import annotations

import json
import math
import sys
import tomllib
from pathlib import Path

import numpy as np
import shapely
from pyproj import Transformer
from shapely.geometry import Point, Polygon, box, shape

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "data/build"
OUT = ROOT / "game/world/tiles"
LUGARES = Path(__file__).resolve().parent / "lugares"
UTM = "EPSG:31982"  # SIRGAS 2000 / UTM 22S, o mesmo do build_tile.py

# Mesmas classes e larguras do build_tile.py (sem importar: ele puxa rasterio e trimesh).
DRIVABLE = {
    "motorway", "trunk", "primary", "secondary", "tertiary", "unclassified",
    "residential", "living_street", "service", "road", "track",
    "motorway_link", "trunk_link", "primary_link", "secondary_link", "tertiary_link",
}
WIDTH_BY_CLASS = {
    "motorway": 12.0, "trunk": 10.0, "primary": 9.0, "secondary": 8.0,
    "tertiary": 7.0, "unclassified": 6.0, "residential": 6.0, "living_street": 5.0,
    "road": 6.0, "service": 4.0, "track": 3.5,
}
LANE_WIDTH = 3.2

CALCADA = 1.5        # o lote começa depois da calçada
CALCADA_SERVICO = 0.5
PISO_CELULA = 3.0    # o piso é recortado em células pra acompanhar o relevo
DEMOLIR_M2 = 5.0     # prédio com mais que isso da pegada dentro do lote sai inteiro

AMARELO = "#f2c200"
BRANCO = "#f4f2ea"
CINZA = "#b9b7b0"
VERDE = "#1f8a4c"
CONCRETO = "#c9c6bd"
ASFALTO = "#55575c"
FAIXA = "#eeeeea"
VIDRO = "#2d3a40"


def road_width(props: dict) -> float:
    try:
        return float(str(props["width"]).replace(",", ".").split()[0])
    except (KeyError, ValueError):
        pass
    try:
        return int(props["lanes"]) * LANE_WIDTH
    except (KeyError, ValueError):
        return WIDTH_BY_CLASS.get(props.get("highway"), 6.0)


class Esquina:
    """Referencial do lugar: u ao longo da `frente`, a partir do cruzamento; v
    perpendicular, entrando no lote (do lado pedido). Metros."""

    def __init__(self, lugar: dict, lines):
        frente = shapely.union_all([ln for ln, p in lines if p.get("name") == lugar["frente"]])
        cruza = shapely.union_all([ln for ln, p in lines if p.get("name") == lugar["esquina"]])
        pts = [g for g in shapely.get_parts(frente.intersection(cruza)) if g.geom_type == "Point"]
        if not pts:
            raise SystemExit(f"{lugar['frente']!r} não cruza {lugar['esquina']!r} no tile")
        self.o = np.array(pts[0].coords[0])
        # Direção da frente saindo do cruzamento: o trecho que começa nele.
        seg = min(shapely.get_parts(frente), key=lambda g: g.distance(pts[0]))
        cs = np.asarray(seg.coords)
        k = int(np.argmin(np.linalg.norm(cs - self.o, axis=1)))
        nxt = cs[k + 1] if k + 1 < len(cs) else cs[k - 1]
        self.du = (nxt - self.o) / np.linalg.norm(nxt - self.o)
        dv = np.array([-self.du[1], self.du[0]])
        sinal = {"leste": dv[0], "oeste": -dv[0], "norte": dv[1], "sul": -dv[1]}[lugar["lado"]]
        self.dv = dv if sinal > 0 else -dv

    def p(self, u: float, v: float) -> np.ndarray:
        return self.o + u * self.du + v * self.dv

    def rect(self, u0, u1, v0, v1) -> Polygon:
        return Polygon([self.p(u0, v0), self.p(u1, v0), self.p(u1, v1), self.p(u0, v1)])

    def rot_y(self) -> float:
        """rotation.y do Godot que leva o eixo X local pra direção u."""
        return math.atan2(self.du[1], self.du[0])

    def rot_placa(self, direcao: np.ndarray) -> float:
        """rotation.y que vira a frente do Label3D (+Z local) pra `direcao` (leste, norte)."""
        return math.atan2(direcao[0], -direcao[1])


class Pecas:
    def __init__(self):
        self.lista = []

    def piso(self, area, cor: str, lift: float = 0.14):
        n = int(math.ceil(max(area.bounds[2] - area.bounds[0], area.bounds[3] - area.bounds[1]) / PISO_CELULA)) + 1
        x0, y0 = area.bounds[0], area.bounds[1]
        tris = []
        for i in range(n):
            for j in range(n):
                cel = box(x0 + i * PISO_CELULA, y0 + j * PISO_CELULA, x0 + (i + 1) * PISO_CELULA, y0 + (j + 1) * PISO_CELULA)
                for part in shapely.get_parts(cel.intersection(area)):
                    if part.geom_type != "Polygon" or part.area < 0.01:
                        continue
                    for t in shapely.get_parts(shapely.constrained_delaunay_triangles(part)):
                        for x, y in np.asarray(t.exterior.coords)[:3]:
                            tris += [round(float(x), 2), round(float(-y), 2)]
        self.lista.append({"tipo": "piso", "cor": cor, "lift": lift, "tris": tris})

    def caixa(self, e: Esquina, u, v, su, sv, h, cor: str, elev=0.0):
        """Caixa alinhada à frente, centro em (u, v), base `elev` acima do chão."""
        x, y = e.p(u, v)
        self.lista.append({"tipo": "caixa", "cor": cor, "x": round(float(x), 2), "z": round(float(-y), 2),
                           "rot_y": round(e.rot_y(), 4), "tam": [su, h, sv], "elev": elev})

    def placa(self, e: Esquina, u, v, elev, texto: str, para: str, px=64, cor="#ffffff", contorno="#00000000"):
        """Texto em (u, v), virado pra `para`: "rua" (-v), "fundo" (+v), "-u" ou "+u"."""
        x, y = e.p(u, v)
        d = {"rua": -e.dv, "fundo": e.dv, "-u": -e.du, "+u": e.du}[para]
        self.lista.append({"tipo": "placa", "texto": texto, "x": round(float(x), 2), "z": round(float(-y), 2),
                           "rot_y": round(e.rot_placa(d), 4), "elev": elev, "px": px, "cor": cor, "contorno": contorno})


def lote(e: Esquina, area: Polygon, pista, dentro: tuple[float, float]):
    """O pedaço de `area` fora da pista que contém o ponto `dentro` (u, v)."""
    livre = area.difference(pista)
    alvo = Point(e.p(*dentro))
    partes = [g for g in shapely.get_parts(livre) if g.geom_type == "Polygon"]
    return min(partes, key=lambda g: g.distance(alvo))


def posto(e: Esquina, lugar: dict, pista, pc: Pecas):
    """Posto de bandeira amarela: cobertura com duas ilhas de bomba, loja de
    conveniência no fundo, totem de preço na esquina. O lote vai até a rua de
    serviço que contorna a quadra, que vira entrada e saída."""
    area = lote(e, e.rect(0, 70, 0, 40), pista, (28, 11))
    pc.piso(area, CONCRETO)
    # Cobertura: placa amarela com forro branco, sobre quatro pilares.
    pc.caixa(e, 28, 11, 16, 9, 0.9, AMARELO, elev=4.6)
    pc.caixa(e, 28, 11, 15.6, 8.6, 0.1, BRANCO, elev=4.5)
    for u in (24, 32):
        pc.caixa(e, u, 11, 1.2, 5.2, 0.22, CINZA)  # ilha
        for v in (9.6, 12.4):
            pc.caixa(e, u, v, 0.35, 0.35, 4.6, CINZA)  # pilar
        for v in (10.5, 11.5):
            pc.caixa(e, u, v, 0.55, 0.7, 1.75, BRANCO, elev=0.22)  # bomba
            pc.caixa(e, u, v, 0.57, 0.72, 0.3, AMARELO, elev=1.7)
    pc.placa(e, 28, 6.45, 4.95, "POSTO", "rua", px=160, cor="#3a2e00")
    # Loja de conveniência.
    pc.caixa(e, 13, 13.5, 8, 6, 3.4, BRANCO)
    pc.caixa(e, 13, 13.5, 8.1, 6.1, 0.6, AMARELO, elev=2.9)
    pc.caixa(e, 13, 10.45, 2.0, 0.1, 2.3, VIDRO)
    pc.placa(e, 13, 10.38, 3.2, "CONVENIÊNCIA", "rua", px=72, cor="#3a2e00")
    # Totem na esquina, lido por quem vem pela frente nos dois sentidos.
    pc.caixa(e, 8.5, 6.4, 0.35, 0.35, 4.4, CINZA)
    pc.caixa(e, 8.5, 6.4, 0.4, 1.8, 2.6, AMARELO, elev=4.2)
    for lado, du in (("-u", -0.22), ("+u", 0.22)):
        pc.placa(e, 8.5 + du, 6.4, 6.1, "POSTO", lado, px=72, cor="#3a2e00")
        pc.placa(e, 8.5 + du, 6.4, 5.0, "GASOLINA  6,29\nETANOL  4,19", lado, px=34, cor="#3a2e00")
    return area


def farmacia(e: Esquina, lugar: dict, pista, pc: Pecas):
    """Farmácia térrea com faixa verde e cruz de bandeira na quina, pátio na
    frente e estacionamento de uma fileira ao lado."""
    nome = lugar["nome"]
    u0, u1, v0, v1 = 7.5, 20.5, 9.5, 17.5
    patio = lote(e, e.rect(u0, u1, 0, v0), pista, ((u0 + u1) / 2, v0 - 1))
    vagas = lote(e, e.rect(u1 + 0.5, 39, 0, 19), pista, (30, 12))
    pc.piso(patio, CONCRETO)
    pc.piso(vagas, ASFALTO)
    uc, vc = (u0 + u1) / 2, (v0 + v1) / 2
    pc.caixa(e, uc, vc, u1 - u0, v1 - v0, 4.4, "#f3f3ef")
    pc.caixa(e, uc, v0 - 0.15, u1 - u0 + 0.3, 0.3, 1.1, VERDE, elev=3.4)
    pc.placa(e, uc, v0 - 0.32, 3.95, nome.upper(), "rua", px=88)
    pc.caixa(e, uc, v0 - 0.05, 3.0, 0.1, 2.5, VIDRO)
    # Cruz de bandeira, perpendicular à fachada, na quina do lado do cruzamento.
    pc.caixa(e, u0 + 0.6, v0 - 0.9, 0.12, 1.3, 0.42, VERDE, elev=3.0)
    pc.caixa(e, u0 + 0.6, v0 - 0.9, 0.12, 0.42, 1.3, VERDE, elev=2.56)
    # Vagas a 90°, de costas pro fundo do lote; corredor do lado da rua.
    for u in np.arange(u1 + 1.5, 38.5, 2.6):
        pc.caixa(e, float(u), 16.5, 0.12, 5.0, 0.03, FAIXA, elev=0.14)
    pc.caixa(e, u1 + 1.5, 6.0, 0.12, 0.12, 2.4, CINZA)
    pc.caixa(e, u1 + 1.5, 6.0, 1.4, 0.12, 0.9, VERDE, elev=2.0)
    pc.placa(e, u1 + 1.5, 5.93, 2.45, "ESTACIONAMENTO", "rua", px=26)
    return shapely.union_all([patio, vagas, e.rect(u0, u1, v0, v1)])


TIPOS = {"posto": posto, "farmacia": farmacia}


def main() -> None:
    cfg = tomllib.loads(Path(sys.argv[1]).read_text())
    over = tomllib.loads((LUGARES / f"{cfg['name']}.toml").read_text())
    to_utm = Transformer.from_crs("EPSG:4326", UTM, always_xy=True)
    ox, oy = to_utm.transform(cfg["center_lon"], cfg["center_lat"])
    localize = lambda g: shapely.transform(g, lambda c: np.column_stack(to_utm.transform(c[:, 0], c[:, 1])) - [ox, oy])

    lines = []
    for raw in (BUILD / f"{cfg['name']}.geojsonseq").read_text().splitlines():
        raw = raw.strip("\x1e").strip()
        if not raw:
            continue
        f = json.loads(raw)
        p = f["properties"]
        if p.get("highway") in DRIVABLE and f["geometry"]["type"] == "LineString":
            lines.append((localize(shape(f["geometry"])), p))
    pista = shapely.union_all([
        ln.buffer(road_width(p) / 2 + (CALCADA_SERVICO if p.get("highway") == "service" else CALCADA))
        for ln, p in lines])

    # Pegadas do Overture usadas no tile (a mesma fonte do build_tile.py).
    predios = [localize(shape(f["geometry"])) for f in
               json.loads((BUILD / over.get("predios", "aneis_overture.geojson")).read_text())["features"]]
    arvore = shapely.STRtree(predios)

    pc = Pecas()
    demolir = []
    for lugar in over["lugar"]:
        e = Esquina(lugar, lines)
        area = TIPOS[lugar["tipo"]](e, lugar, pista, pc)
        saem = [predios[i] for i in arvore.query(area)
                if predios[i].intersection(area).area > DEMOLIR_M2]
        for g in saem:
            for part in shapely.get_parts(g.buffer(0.5, join_style="mitre")):
                demolir.append([[round(float(x), 2), round(float(-y), 2)] for x, y in np.asarray(part.exterior.coords)[:-1]])
        print(f"{lugar['tipo']} ({lugar['frente']} × {lugar['esquina']}, {lugar['lado']}): "
              f"lote {area.area:.0f} m², {len(saem)} prédios demolidos")

    out = OUT / f"{cfg['name']}.lugares.json"
    out.write_text(json.dumps({"demolir": demolir, "pecas": pc.lista}, ensure_ascii=False) + "\n")
    print(f"{out.relative_to(ROOT)}: {len(pc.lista)} peças")


if __name__ == "__main__":
    main()
