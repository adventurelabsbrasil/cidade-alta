# /// script
# requires-python = ">=3.11"
# dependencies = ["pyproj"]
# ///
"""Leva os pontos de descoberta (decisões 008, 010 e 011) para o referencial de um tile.

Lê data/build/pontos_anel1.json (saída de medir_pontos.py) e grava
game/world/tiles/<tile>.pontos.json com o gatilho de cada ponto em coordenadas
do Godot (x leste, z = -norte), na mesma projeção do build_tile.py. Só entram os
pontos dentro do tile; o resumo (peso total e limiar do anel) é o do anel inteiro.

Uso:
    uv run pipeline/pontos_tile.py pipeline/tiles/fatia.toml
"""

from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path

from pyproj import Transformer

ROOT = Path(__file__).resolve().parent.parent
PONTOS = ROOT / "data/build/pontos_anel1.json"
OUT = ROOT / "game/world/tiles"
UTM = "EPSG:31982"  # SIRGAS 2000 / UTM 22S, o mesmo do build_tile.py


def main() -> None:
    cfg = tomllib.loads(Path(sys.argv[1]).read_text())
    half = cfg["size_m"] / 2
    to_utm = Transformer.from_crs("EPSG:4326", UTM, always_xy=True)
    ox, oy = to_utm.transform(cfg["center_lon"], cfg["center_lat"])
    data = json.loads(PONTOS.read_text())

    pontos = []
    for p in data["pontos"]:
        x, y = to_utm.transform(p["gatilho_lon"], p["gatilho_lat"])
        x, y = x - ox, y - oy
        if abs(x) > half or abs(y) > half:
            continue
        pontos.append({"id": p["id"], "nome": p["nome"], "categoria": p["categoria"],
                       "peso": p["peso"], "landmark": p["landmark"], "x": round(x, 1), "z": round(-y, 1)})

    out = OUT / f"{cfg['name']}.pontos.json"
    out.write_text(json.dumps({"anel": data["resumo"], "pontos": pontos}, ensure_ascii=False, indent=1) + "\n")
    print(f"{out.relative_to(ROOT)}: {len(pontos)} de {len(data['pontos'])} pontos dentro do tile")


if __name__ == "__main__":
    main()
