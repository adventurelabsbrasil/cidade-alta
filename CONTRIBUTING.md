# Como contribuir

Contribuições são bem-vindas: código, landmarks, carros, ajustes de dados.

## Licenças

| O que você envia | Licença |
|---|---|
| Código | MIT (`LICENSE`) |
| Assets feitos à mão | CC BY 4.0 (`assets/LICENSE`) |
| Dados derivados do OSM | ODbL (`data/osm/LICENSE`) |

Ao enviar, você concorda que sua contribuição seja publicada sob a licença da camada correspondente.

## DCO: assine seus commits

Usamos o [Developer Certificate of Origin](https://developercertificate.org/). Cada commit precisa da linha `Signed-off-by`, que atesta que você tem direito de enviar aquele conteúdo:

```bash
git commit -s -m "sua mensagem"
```

## Regras do projeto

- **Jogo original.** Nada de nome, logo, personagem, UI ou estética copiada de jogos existentes.
- **Sem marcas reais.** Fachadas usam placas genéricas ("PADARIA", "MERCADO").
- **Sem dados pessoais.** Nada de endereço residencial, nome de morador ou placa de veículo real.
- **Pipeline reprodutível.** Não edite à mão a malha gerada; ajustes vão em arquivos de override versionados.
- **Sem Google Maps/Street View como fonte.** Isso viola os termos deles.

## Decisões de projeto

As decisões ficam em [`docs/decisoes/`](docs/decisoes/), e o mapa de decisões em aberto está na [issue #1](https://github.com/adventurelabsbrasil/cidade-alta/issues/1).
