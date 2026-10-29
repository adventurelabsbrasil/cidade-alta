# 008 — Progressão

- **Status:** decidido (29/10/2026)
- **Ticket:** #8 · **Mapa:** #1

## Decisão

1. **A moeda é a descoberta.** Km rodados não contam. O que avança o jogo é achar lugares da cidade.
2. **Como se descobre:** passando perto do ponto, sem marcador. Cada ponto tem uma zona invisível em volta; ao entrar nela, aparece um cartão com o nome real do lugar. O mapa mostra só "?" na região de um ponto ainda não achado.
3. **De onde vêm os pontos:**
   - **Automáticos:** o pipeline extrai do OSM os pontos com as tags de uma lista (praças, igrejas, escolas, mirantes, pontes, saídas de estrada…). Isso é reprodutível e cobre os anéis externos sem curadoria.
   - **Landmarks:** os 5–10 feitos à mão (decisão 001) também são pontos e valem mais.
   - O ID de cada ponto é estável: o id do OSM ou o id do landmark.
4. **Abrir o próximo anel:** descobrir uma **porcentagem dos pontos do anel atual**. O valor começa em **60%** e se ajusta jogando.
5. **Borda de anel trancado:**
   - O pipeline põe cavaletes de obra/desvio em cada cruzamento de via com o círculo da borda.
   - Além da borda, neblina.
   - Fora da rua, uma barreira suave freia o carro e empurra de volta.
   - Sem polícia e sem parede invisível seca.
6. **Raios dos anéis: 2,1 / 3,5 / 5 km**, a partir do Pátio Urbano. Isso substitui o 1,5 / 3 / 5 da decisão 005.
   - O anel 1 cresce para conter inteiras as grandes vias que ligam a cidade (tabela abaixo). Assim dá pra rodar a cidade toda por elas desde o início.
   - A Francisco J. Lopes segue para fora da cidade; o bloqueio dela a ~2,1 km é a porta para o anel 2.
   - O **spawn na Av. Borges de Medeiros não muda.** A Borges vai até 1.575 m e fica ~525 m dentro da borda.
7. **Além dos anéis:** alguns pontos descobertos viram **largada de racha** naquele trecho. O formato do racha é um item à parte no mapa. Os **3 carros ficam livres desde o início**, como na decisão 006.
8. **Save:** um JSON com os IDs descobertos em `user://` do Godot, gravado a cada descoberta. Slots, nuvem e o resto ficam no item "Save / persistência" do mapa.

## Na v0

Entram os pontos do anel 1, o cartão de descoberta, o contador ("23/40") e os bloqueios na borda. Ao bater a porcentagem, o jogo mostra "anel 2 em breve". Os anéis 2 e 3 entram nas versões seguintes, junto com o streaming (decisão 007).

## Medições (OSM, centro no Pátio Urbano)

### Grandes vias do anel 1

| Via | Distância ao centro | Extensão |
|---|---|---|
| Rua Cel. Vitor Vila Verde | 50–977 m | 2,1 km |
| Av. Paulo Maciel de Moraes | 70–1.107 m | 2,5 km |
| Rua Santo Antônio | 116–1.245 m | 1,3 km |
| Rua Maurício Cardoso | 1.243–1.479 m | 1,5 km |
| Av. Borges de Medeiros | 1.384–1.575 m | 1,9 km |
| Rua Cel. Francisco Borges de Lima | 128–1.857 m | 2,3 km |
| Av. Afonso Porto Emerim | 260–2.013 m | 3,6 km |
| Rua João Pedroso da Luz | 467–2.066 m | 2,1 km |
| Rua Francisco J. Lopes | 90–5.221 m | 5,9 km (sai da cidade) |

### Conteúdo por faixa

| Faixa | km de via (todas as `highway`) | Prédios Overture |
|---|---|---|
| 0–2,1 km | 156 | 13.738 |
| 2,1–3,5 km | 77 | 3.256 |
| 3,5–5 km | 64 | 2.453 |

Os km de via aqui contam todas as linhas `highway` do recorte, então não batem com a tabela da decisão 007.

## A medir

- **FPS do anel 1 em 2,1 km:** ~+28% de prédios sobre o tile de 1,5 km, que rodava a 190 FPS. Pode ser que ainda não precise de streaming.
- **Pontos por anel:** quantos pontos a lista de tags gera em cada anel. Isso calibra os 60%.
