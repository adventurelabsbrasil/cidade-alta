# Cidade Alta

Jogo de exploração open source: escolha um carro e dirija livremente por **Santo Antônio da Patrulha/RS**, recriada a partir de dados reais de mapa, em estilo low-poly. Sem missões, sem sair do carro: só a cidade, o volante e o que está depois da próxima esquina.

> 🚧 Protótipo. Já dá pra dirigir num quarteirão real da Av. Borges de Medeiros (a [fatia vertical](docs/decisoes/007-fatia-vertical.md)). Acompanhe o [mapa de decisões](https://github.com/adventurelabsbrasil/cidade-alta/issues/1).

## Jogar a fatia vertical

Precisa de um Mac com Apple Silicon e do [Godot 4.6+](https://godotengine.org/download/macos/) (`brew install --cask godot`).

```bash
godot --path game
```

`W`/`S` acelera e freia, `A`/`D` vira, `Espaço` é o freio de mão, `C` troca a câmera e `R` volta pro início. Gamepad também funciona.

Passe perto de um lugar da cidade (praça, igreja, escola, bairro…) e aparece um cartão com o nome dele. O progresso fica em `~/Library/Application Support/Godot/app_userdata/Cidade Alta/descobertas.json`; apague o arquivo para começar do zero.

## Gerar a cidade

O tile `game/world/tiles/fatia.glb` já vem no repo. Para gerar de novo a partir dos dados (precisa de [uv](https://docs.astral.sh/uv/) e `brew install osmium-tool`):

```bash
mkdir -p data/osm/raw data/dem/raw
curl -L -o data/osm/raw/sul-latest.osm.pbf https://download.geofabrik.de/south-america/brazil/sul-latest.osm.pbf
curl -L -o data/dem/raw/cop30_S30_W051.tif https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_S30_00_W051_00_DEM/Copernicus_DSM_COG_10_S30_00_W051_00_DEM.tif
uv run pipeline/build_tile.py pipeline/tiles/fatia.toml
```

Os pontos de descoberta ([decisão 011](docs/decisoes/011-pontos-de-descoberta.md)) também já vêm no repo. Para gerar de novo:

```bash
uv run pipeline/medir_aneis.py
python3 pipeline/medir_pontos.py data/build/aneis.geojsonseq data/build/pontos_anel1.json
uv run pipeline/pontos_tile.py pipeline/tiles/fatia.toml
```

## O que já está decidido

| | |
|---|---|
| **Engine** | Godot 4.6+ com GDScript |
| **Visual** | low-poly estilizado, ciclo dia/noite |
| **Cidade** | OpenStreetMap + Overture Maps + relevo Copernicus, gerada por script reprodutível |
| **Área** | começa na Av. Borges de Medeiros; anéis de até 5 km que se abrem explorando |
| **Carros** | 3 arquétipos originais, física arcade com peso |
| **Plataforma** | macOS nativo (Apple Silicon), renderização Metal |

Detalhes e justificativas em [`docs/decisoes/`](docs/decisoes/).

## Contribuir

Veja [CONTRIBUTING.md](CONTRIBUTING.md). Commits usam DCO (`git commit -s`).

## Licenças

- Código: [MIT](LICENSE)
- Assets: [CC BY 4.0](assets/LICENSE)
- Dados de mapa: [ODbL](data/osm/LICENSE), © OpenStreetMap contributors
- Relevo: [Copernicus](data/dem/NOTICE)

Créditos completos em [ATTRIBUTION.md](ATTRIBUTION.md).
