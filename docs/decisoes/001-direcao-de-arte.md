# 001 — Direção de arte

- **Status:** decidido (29/10/2026)
- **Ticket:** #5 · **Mapa:** #1

## Contexto

O jogo recria Santo Antônio da Patrulha/RS a partir de dados reais de mapa. A medição do OSM (ver #3) mostrou malha viária razoável, mas só ~400 prédios mapeados (de uma ordem de grandeza de 10 mil esperados) e nenhum com altura. A direção de arte precisa ser barata de gerar a partir de dado incompleto e fácil de a comunidade contribuir.

## Decisão

1. **Linguagem visual: low-poly estilizado.** Formas simples, cores chapadas de uma paleta única (atlas), sem texturas fotográficas. O OSM extrudado já fica coerente nesse estilo.
2. **Prédios: pegadas do Overture Maps + gerador procedural.** Onde houver pegada real (OSM + Microsoft + Google via Overture), ela é usada. Onde faltar, um gerador preenche os lotes vazios com casas low-poly genéricas por tipo de zona. Altura por heurística (1–2 pavimentos residencial, mais no centro), com ajuste manual.
3. **Feito à mão: lista curta + porta para a comunidade.** A v0 tem de 5 a 10 landmarks escolhidos e modelados à mão. Depois, um formato padrão (glTF + ponto no mapa + licença) permite que a comunidade envie novos landmarks por PR.
4. **Luz: ciclo dia/noite simples.** Céu degradê que muda ao longo de um dia curto, com postes acendendo à noite.
5. **Fachadas: placas genéricas sem nome** ("PADARIA", "MERCADO", ícones). Nada de nomes ou logos de comércios reais.

## Fora desta decisão

- A lista concreta dos landmarks da v0
- O formato exato de contribuição de landmark
- Clima (chuva, neblina)
