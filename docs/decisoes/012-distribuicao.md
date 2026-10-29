# 012 — Distribuição

- **Status:** decidido (29/10/2026)
- **Ticket:** #15 · **Mapa:** #1

## Decisão

1. **v0:** **GitHub Releases** é a fonte oficial e o **itch.io** é a vitrine, os dois alimentados pelo mesmo workflow.
2. **Mac:** o `.app` (Universal 2) vai com **assinatura ad-hoc**, que o export do Godot já faz, **sem notarização**. Custo zero. Sem assinatura nenhuma o app não roda em Apple Silicon.
3. **Depois:** builds de Windows e Linux entram como canais a mais; Flathub para Linux. Notarização da Apple (Apple Developer Program, anual) só se o atrito no Mac virar reclamação. Steam e Homebrew ficam fora: Steam é pesado para um hobby, e o Homebrew passou a exigir cask que passe no Gatekeeper.

## O que o jogador de Mac vê

**Sem notarização** (Sequoia em diante): "Apple could not verify…", só com *Done* e *Move to Trash*. O Ctrl+clique > Abrir não existe mais. Passos para o README e a página:

1. Abrir o jogo uma vez e clicar em *Done*.
2. **Ajustes do Sistema > Privacidade e Segurança > Abrir Mesmo Assim** (o botão some em ~1 h).
3. Autenticar e clicar em *Abrir*. A exceção fica salva.
4. Plano B: mover para `/Applications` e rodar `xattr -dr com.apple.quarantine /Applications/CidadeAlta.app`.

**Com notarização:** um único diálogo com *Abrir*.

## CI (GitHub Actions, em tag `v*`)

1. `ubuntu-latest` com Godot 4.6 e os export templates da mesma versão.
2. Gerar os tiles com o `pipeline/` (`data/build/` e os `.glb` grandes estão no gitignore), com o extract em cache.
3. `godot --headless --path game --export-release "macOS" out/CidadeAlta-mac.zip`.
4. `gh release create $TAG out/* dados-odbl.zip`.
5. `butler push out/CidadeAlta-mac.zip <usuario>/cidade-alta:mac --userversion $TAG`, com o secret `BUTLER_API_KEY`.
6. Notarização futura: `rcodesign` no próprio Linux ou `notarytool` num runner macOS.

## Licenças (decisão 004)

- **Dentro do build:** tela de créditos e, no zip, `ATTRIBUTION.md`, `LICENSE`, `assets/LICENSE`, `data/osm/LICENSE` e `data/dem/NOTICE`.
- **ODbL §4.3:** "© OpenStreetMap contributors, ODbL" com link para openstreetmap.org/copyright, visível sem o jogador clicar em nada (abertura ou menu).
- **ODbL §4.6:** a base derivada do OSM precisa ser oferecida de graça, em formato que máquina leia. Hoje ela fica no gitignore e ninguém a recebe. Cada Release anexa um **`dados-odbl.zip`** com os GeoJSON processados, o `data/osm/LICENSE` e o comando do pipeline.
- **Página do itch e notas da Release:** bloco de atribuição (OSM, Overture, Copernicus, Godot, autores CC-BY) com link para o `ATTRIBUTION.md`.

## A confirmar

- O *Abrir Mesmo Assim* no macOS Tahoe 26.x: a Apple ainda documenta, fontes de terceiros divergem. Testar no MacBook do Founder antes da v0.

## Fontes

- https://docs.godotengine.org/en/stable/tutorials/export/exporting_for_macos.html
- https://docs.godotengine.org/en/stable/tutorials/export/running_on_macos.html
- https://support.apple.com/en-us/102445
- https://developer.apple.com/programs/enroll/
- https://eclecticlight.co/2026/08/11/how-can-you-run-code-that-hasnt-been-notarised/
- https://www.idownloadblog.com/apple-macos-sequoia-gatekeeper-change-install-unsigned-apps-mac/
- https://www.osnews.com/story/141055/bug-or-intentional-macos-15-1-completely-removes-ability-to-launch-unsigned-applications/
- https://itch.io/docs/creators/payments
- https://itch.io/docs/butler/pushing.html
- https://itch.io/docs/butler/login.html
- https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases
- https://partner.steamgames.com/doc/gettingstarted/appfee
- https://docs.brew.sh/Acceptable-Casks
- https://docs.brew.sh/Deprecating-Disabling-and-Removing-Casks
- https://opendatacommons.org/licenses/odbl/1-0/
- https://osmfoundation.org/wiki/Licence/Attribution_Guidelines
