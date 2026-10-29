# 007 — Fatia vertical: viabilidade

- **Status:** protótipo validado (29/10/2026)
- **Ticket:** #9 · **Mapa:** #1

## O que foi construído

Um tile real de 800 m × 800 m em volta da Av. Borges de Medeiros e o carro compacto dirigível, rodando nativo no MacBook (Apple M4).

- **Pipeline** (`pipeline/build_tile.py`): osmium sobre o extract da Geofabrik, prédios do Overture, relevo Copernicus GLO-30, ruas por shapely + trimesh, um `.glb` por tile. Roda em ~9 s e gera o mesmo resultado a cada execução.
- **Jogo** (`game/`): Godot 4.7, carro próprio com uma raycast por roda sobre o Jolt, câmera de 3ª pessoa e de capô, teclado e gamepad.

## Medições

| Pergunta (de onde veio) | Resultado |
|---|---|
| Metal vs Vulkan no MacBook (002) | **Metal 297 FPS, p99 3,7 ms** · Vulkan/MoltenVK 145 FPS, p99 7,1 ms. O Metal virou o driver padrão. |
| Precisa de streaming? (002) | **Não na v0.** O anel 1 inteiro num tile só (10.755 prédios, 713 vias, 529 mil triângulos, glb de 11 MB) roda a **190 FPS, p99 6,1 ms**. A pergunta volta nos anéis 2 e 3. |
| `VehicleBody3D` serve? (002, 006) | Não foi preciso. O carro por raycast assenta, acelera, freia, dá ré, segura na ladeira e desliza com o freio de mão. |
| Coordenada do centro (005) | **Pátio Urbano**: nó `shop=mall` em -29,83057, -50,52438 (Rua Coronel Vitor Vila Verde). |
| Spawn dentro do anel 1? (005) | **Por pouco.** A Borges fica a 1.379–1.574 m do centro, então um trecho sai do anel 1. O ponto de spawn fica a ~1.490 m. |
| Vias e prédios por anel (005) | Tabela abaixo. |

Os números de FPS são da câmera girando em volta do carro e sobrevoando o tile, em 1600×900 com sombra e MSAA 2×, sem vsync.

### Conteúdo por anel (centro no Pátio Urbano)

| Anel | Vias | km de via | Prédios OSM | Prédios Overture |
|---|---|---|---|---|
| até 1,5 km | 492 | 98,5 | 48 | 9.627 |
| 1,5 a 3 km | 500 | 103,3 | 29 | 6.536 |
| 3 a 5 km | 131 | 88,3 | 12 | 3.291 |

O OSM quase não tem prédio desenhado na cidade. Sem o Overture, a cidade seria um campo vazio com ruas.

## De onde vêm os prédios

O release `2026-10-21.0` do Overture (tema `buildings`, ODbL) junta três fontes aqui: **Google Open Buildings** (~74%), **Microsoft ML Buildings** (~25%) e OSM (<1%). O Google Open Buildings é um dataset aberto (CC BY 4.0 / ODbL), diferente do Google Maps, que o CONTRIBUTING proíbe como fonte. A atribuição está no `ATTRIBUTION.md`.

## O que fica para depois

- **Sensação do carro:** só o Founder dirigindo diz se está "arcade com peso". Os parâmetros ficam todos expostos no `car.gd`.
- **Spawn na fronteira do anel 1:** decidir entre mover o spawn para o trecho sul da Borges ou crescer o anel 1 para ~1,6 km. Isso entra na Progressão (#8).
- **Gerador procedural de lotes vazios (001):** não foi preciso na fatia, porque o Overture já cobre a área densa.
- **Pista sem calçada, meio-fio nem faixa.** Prédios sem telhado e sem fachada. Ficam para o passo de arte.
