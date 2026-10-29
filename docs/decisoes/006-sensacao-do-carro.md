# 006 — Sensação do carro

- **Status:** decidido (29/10/2026)
- **Ticket:** #7 · **Mapa:** #1

## Decisão

1. **Física: arcade com peso.** O carro responde fácil no teclado ou no controle e perdoa erro, mas tem inércia, rolagem de carroceria e drift controlável. A implementação é um carro próprio com raycast sobre o Jolt (risco previsto na decisão 002), e não o `VehicleBody3D` puro.
2. **Carros na v0: 3 arquétipos originais**, sem marca nem modelo real:
   - **Compacto popular:** ágil e leve.
   - **Sedã/hatch médio:** equilibrado.
   - **Picape:** pesada, boa na estrada de chão (anéis externos, decisão 005).

   Os três usam o mesmo código de física, mudando só os parâmetros (massa, potência, aderência, suspensão). A escolha do carro no início já existe na v0.
3. **Câmera e controle:** terceira pessoa atrás do carro, com opção de câmera no capô. Teclado e gamepad. Volante e câmera de cockpit ficam para depois.

## Implicação para a fatia vertical (#9)

A fatia valida a física com **um** dos arquétipos (o compacto). Os outros dois entram como ajuste de parâmetros depois que a sensação estiver boa.
