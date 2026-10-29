# Cidade Alta

Jogo de exploração open source: escolha um carro e dirija livremente por **Santo Antônio da Patrulha/RS**, recriada a partir de dados reais de mapa, em estilo low-poly. Sem missões, sem sair do carro: só a cidade, o volante e o que está depois da próxima esquina.

> 🚧 Fase de planejamento. Ainda não há nada jogável. Acompanhe o [mapa de decisões](https://github.com/adventurelabsbrasil/cidade-alta/issues/1).

## O que já está decidido

| | |
|---|---|
| **Engine** | Godot 4.6+ com GDScript |
| **Visual** | low-poly estilizado, ciclo dia/noite |
| **Cidade** | OpenStreetMap + Overture Maps + relevo Copernicus, gerada por script reprodutível |
| **Área** | começa na Av. Borges de Medeiros; anéis de até 5 km que se abrem explorando |
| **Carros** | 3 arquétipos originais, física arcade com peso |
| **Plataforma** | macOS nativo (Apple Silicon) |

Detalhes e justificativas em [`docs/decisoes/`](docs/decisoes/).

## Contribuir

Veja [CONTRIBUTING.md](CONTRIBUTING.md). Commits usam DCO (`git commit -s`).

## Licenças

- Código: [MIT](LICENSE)
- Assets: [CC BY 4.0](assets/LICENSE)
- Dados de mapa: [ODbL](data/osm/LICENSE), © OpenStreetMap contributors
- Relevo: [Copernicus](data/dem/NOTICE)

Créditos completos em [ATTRIBUTION.md](ATTRIBUTION.md).
