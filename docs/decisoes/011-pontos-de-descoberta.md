# 011 — Pontos de descoberta: tags e calibragem

- **Status:** decidido (29/10/2026)
- **Ticket:** #12 · **Mapa:** #1

## Decisão

1. **Tags que viram ponto:** `leisure=park`, `amenity=place_of_worship`/`building=church`, escolas e universidades, `tourism=viewpoint`/`attraction`, prédios públicos (hospital, fórum, bombeiros, rodoviária, posto de saúde…), pontes em via dirigível, rotatórias e **bairros** (`place=neighbourhood`/`hamlet`). O cartão de bairro ("Bairro Cidade Alta") é o que mais ajuda os anéis externos.
2. **Ficam de fora:** postos e lojas (são marcas, não lugares), caixas d'água, campos e cemitérios (não têm nome no OSM).
3. **Filtros:**
   - precisa ter `name`; ponte e rotatória podem herdar o nome da via;
   - nome genérico sai ("Área Verde…", "Quadra esportiva pública");
   - até **60 m** de uma via dirigível; bairro até 250 m, com a zona de gatilho levada para a via mais próxima;
   - deduplicação: nó e área do mesmo lugar, mesmo nome a menos de 400 m, ponte por (via, curso d'água), rotatórias a menos de 80 m.
4. **Abrir o próximo anel:** `max(ceil(60% × peso do anel), 10)`.
5. **Piso de 15 pontos por anel** antes de liberar o anel. Abaixo disso, completa-se com pontos curados à mão (sem modelo 3D) ou com edições no OSM.

## Medição (anel 1 em 2,1 km)

| | Anel 1 | Anel 2 | Anel 3 |
|---|---|---|---|
| Pontos automáticos | 35 | 6 | 7 |
| Trocados por landmark (decisão 010) | −4 | — | — |
| Landmarks, peso 2 | 5 × 2 | — | — |
| **Peso total** | **41** | 6 | 7 |
| **Para abrir o próximo** | **25** | abaixo do piso | abaixo do piso |
| km de via | 156 | 77 | 64 |

Dá cerca de um ponto a cada 4,5 km de via no anel 1: não vira checklist, e sobram 16 de peso opcional.

Por categoria (com nome / sem nome):

| Categoria | Anel 1 | Anel 2 | Anel 3 |
|---|---|---|---|
| parque/praça | 13 / 5 | 1 / 0 | 0 / 0 |
| igreja | 2 / 0 | 0 / 0 | 2 / 0 |
| escola/universidade | 4 / 1 | 1 / 0 | 0 / 0 |
| mirante/atração | 0 / 0 | 0 / 0 | 1 / 0 |
| prédio público | 5 / 0 | 0 / 0 | 0 / 1 |
| ponte | 4 / 1 | 0 / 1 | 0 / 0 |
| rotatória | 0 / 2 | 0 / 0 | 0 / 0 |
| bairro | 8 / 0 | 5 / 0 | 4 / 0 |

Medido com `pipeline/medir_pontos.py` sobre `data/build/aneis.geojsonseq`, centro no Pátio Urbano.

## Lacunas do OSM

- Não estão no OSM: Prefeitura, Câmara, Brigada Militar e Correios (só a "Praça dos Correios").
- Só 4 igrejas em 5 km e um único mirante (Trilha da Cachaça).
- Nenhuma via com `bridge` cruza arroio com nome. Os arroios Veadinho, Pitangueiras e Passo dos Ramos e o Rio dos Sinos estão no mapa; só uma via sem nome cruza o Veadinho (anel 2), sem `bridge`.

## Para o pipeline

- O `osmium export` padrão não grava o id do OSM. Para o ID estável da decisão 008, exportar com `--add-unique-id=type_id`.
- Os anéis 2 e 3 precisam de curadoria até o piso de 15 antes de entrarem (junto com o streaming, decisão 007). Candidatos: a travessia do Arroio Veadinho, o bairro Passo dos Ramos (a 554 m da via), as entradas das estradas com nome (8 no anel 2, 6 no anel 3).

## Fontes

Referências qualitativas de design; não há limiar numérico publicado.

- https://www.strayspark.studio/blog/open-world-design-pacing-player-freedom
- https://www.gamedeveloper.com/design/how-to-make-catchy-collectibles
- https://www.gamespew.com/2021/11/the-real-joy-of-forza-horizon-5-is-road-discovery/
