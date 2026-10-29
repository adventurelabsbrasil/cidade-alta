# 003 — Pipeline dado real → 3D

- **Status:** decidido (29/10/2026)
- **Ticket:** #3 · **Mapa:** #1

## Contexto (medição de 29/10/2026, Overpass)

O município de Santo Antônio da Patrulha/RS tem 2.033 vias no OSM (1.642 veiculares), mas poucos atributos: só ~5% têm `lanes`. Prédios são 399, nenhum com altura. A área tem ~1.000 km², então a v0 fica no núcleo urbano (o recorte é decidido no ticket #6).

## Decisão

1. **Extração:** recorte `sul-latest.osm.pbf` da Geofabrik pelo polígono do município, com `osmium extract` e `osmium tags-filter`. Overpass só para iterar rápido.
2. **Prédios:** pegadas do Overture Maps + gerador procedural nos lotes vazios, altura por heurística (ver decisão 001).
3. **Relevo:** Copernicus GLO-30, reprojetado com GDAL para UTM 22S, heightmap de 16 bits, suavizado e achatado no corredor das vias. A atribuição e o disclaimer vão no `ATTRIBUTION.md` (ver #4).
4. **Ruas dirigíveis:** script Python próprio (shapely + trimesh). Largura por classe de via (ou por `lanes`), geometria de interseção e "carve" do terreno sob a pista. O script exporta glTF.
5. **Montagem:** glTF por tile (chunks de 500 m a 1 km), importado no Godot (ver decisão 002). O Blender fica só para os landmarks feitos à mão.

## Princípio

O pipeline é **um script reprodutível**: rodar de novo sobre um extract mais novo gera a cidade atualizada. Nada de edição manual na malha gerada. Ajustes ficam em arquivos de configuração (overrides) versionados.

## Alternativas descartadas

- **Addon Road Generator do Godot:** amarra o pipeline ao editor e pesa com mais de 1.600 vias.
- **OSM2World:** as interseções não servem para física de direção.
