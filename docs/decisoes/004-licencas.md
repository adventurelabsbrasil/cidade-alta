# 004 — Licenças

- **Status:** decidido (29/10/2026)
- **Ticket:** #4 · **Mapa:** #1
- _Não é parecer jurídico. Antes de um release público, vale uma revisão rápida com advogado._

## Decisão

| Camada | Licença | Onde |
|---|---|---|
| Código | **MIT** | `LICENSE` |
| Assets feitos à mão (landmarks, carros, modelos) | **CC-BY 4.0** | `assets/LICENSE` |
| Dados OSM processados (extracts, GeoJSON, tiles) | **ODbL 1.0** (obrigatória) | `data/osm/LICENSE` |
| Relevo Copernicus GLO-30 | Licença Copernicus (aviso + disclaimer) | `data/dem/NOTICE` |
| Contribuições | **DCO** (`git commit -s`) | `CONTRIBUTING.md` |

Atribuição consolidada em `ATTRIBUTION.md` e na tela de créditos do jogo.

## Por quê

- **MIT** combina com o Godot, tem o menor atrito pra contribuir e permite reuso livre. A troca é aceita: permite fork fechado.
- **CC-BY 4.0** segue a mesma linha de liberdade e garante crédito a quem contribui.
- **ODbL** não é escolha nossa. Dado derivado do OSM é Derivative Database e carrega share-alike. A cena 3D compilada é tratada como Produced Work (zona cinzenta, já que o guideline da OSMF não cita jogos).
- **DCO** é leve e deixa rastro de que quem contribui tem direito sobre o que envia.

## Cuidados

- Um asset modelado a partir da geometria do OSM pode herdar a ODbL. Assets 100% autorais não herdam.
- Confirmar o texto exato da licença Copernicus no PDF oficial antes do release.
- Marcas: nada de nome, logo ou UI de jogos existentes, e nenhuma marca de comércio real (ver decisão 001).
