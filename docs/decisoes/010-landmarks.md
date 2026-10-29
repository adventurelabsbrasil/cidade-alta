# 010 — Landmarks da v0

- **Status:** decidido (29/10/2026)
- **Ticket:** #14 · **Mapa:** #1

## Decisão

1. **5 landmarks feitos à mão na v0**, o piso da decisão 001. As vagas 6–10 ficam para contribuição via PR, que também serve de teste do formato de contribuição.
2. **A lista**, escolhida pelo Founder (quem é da cidade):

| Landmark | O que se modela | Do centro | Grande via mais próxima |
|---|---|---|---|
| Pátio Urbano | o centro dos anéis, marco de origem | 0 m | Cel. Vitor Vila Verde, 42 m |
| Igreja N. Sra. da Boa Viagem | a igreja do centro, de tijolo à vista | 408 m | Cel. Vitor Vila Verde, 91 m |
| Igreja Matriz (Paróquia Santo Antônio) | a matriz da Cidade Alta, ao lado do Colégio Santa Teresinha | 1.215 m | Av. Paulo Maciel de Moraes, 159 m |
| Fonte Imperial | a fonte **e a praça inteira** (muretas, caminhos, árvores), para ser lida a 50 km/h | 1.531 m | Av. Borges de Medeiros, 104 m |
| Rodoviária | o prédio da rodoviária | 1.546 m | Av. Afonso Porto Emerim, 123 m |

   Todos estão no anel 1 (2,1 km) e a até 160 m de uma das grandes vias da decisão 008. As distâncias usam o centroide do OSM.

3. **"Valer mais" (decisão 008) quer dizer:**
   - **peso 2** na contagem para abrir o próximo anel;
   - **silhueta no mapa** desde o início, no lugar do "?", servindo de farol para a exploração;
   - **cartão especial**, com o nome e uma linha de história.
4. **O landmark substitui o ponto automático do mesmo lugar.** A Boa Viagem, a Paróquia Santo Antônio, a Praça da Fonte Imperial e a Rodoviária já saem da lista de tags (decisão 011); o pipeline troca esses pontos pelo landmark, com o id do landmark.

## Fora do OSM

O Founder citou a Matriz como "Igreja Matriz"; no OSM ela é "Paróquia Santo Antônio". O cartão usa o nome que a cidade usa (Igreja Matriz). O OSM da cidade é ralo: não tem Prefeitura, Câmara nem Correios (decisão 011).

## A decidir depois

- Formato de contribuição de landmark (glTF + ponto no mapa + licença), já no mapa.
- Se a Praça N. Sra. da Boa Viagem, em frente à igreja, entra no landmark (como na Fonte) ou fica um ponto à parte.
- O texto de história de cada cartão.
