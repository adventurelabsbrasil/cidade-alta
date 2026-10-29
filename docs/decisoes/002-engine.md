# 002 — Engine

- **Status:** decidido (29/10/2026)
- **Ticket:** #2 · **Mapa:** #1

## Decisão

**Godot 4.6+ com GDScript**, física Jolt (padrão desde a 4.6), renderização Forward+ e assets importados em glTF.

## Por quê

- Cobre dirigir, mundo aberto e cidade gerada do OSM sem precisar escrever um motor.
- O GDScript tem o maior volume de exemplos, então agentes de IA erram menos. Não tem build step, e quem chega da comunidade começa rápido.
- As cenas são em texto (`.tscn`), fáceis de diffar e de revisar em PR.
- A licença é MIT, compatível com o projeto open source.

## Alternativas descartadas

- **Godot + C#:** exige SDK .NET, tem menos exemplos e mais atrito no export.
- **Bevy:** API instável a cada versão 0.x e nenhum crate de veículo maduro.
- **O3DE, raylib, three.js:** suporte fraco no macOS ou exigem fazer tudo à mão.

## Riscos aceitos (a validar na fatia vertical, #9)

- O `VehicleBody3D` é básico, então provavelmente vamos precisar de um carro próprio com raycast sobre o Jolt.
- O streaming depende de addons (Terrain3D, Open World Database). Medir se o núcleo urbano precisa disso antes de adotar.
- Testar Metal vs Vulkan/MoltenVK no MacBook, por causa de relatos de regressão de FPS no M1.
