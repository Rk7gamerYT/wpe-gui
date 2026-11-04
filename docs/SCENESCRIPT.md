# Compatibilidade SceneScript no fork

O motor está em desenvolvimento. Renderizar uma imagem não comprova que todos os scripts,
efeitos e interações do wallpaper estejam funcionando. A bateria de integração verifica
as funções de forma explícita e a auditoria da biblioteca registra as falhas restantes.

## Base implementada e testada

- Módulos ES, incluindo importações de `WEMath`, `WEColor`, `WEVector` e arquivos JS do
  próprio wallpaper. Módulos desconhecidos geram erros identificando o nome.
- Avaliação dos scripts após criar o grafo de camadas; `init` em ordem de criação e
  dependências, antes de `applyUserProperties` e `update`. `destroy` roda antes de liberar as camadas.
- Camadas de grupo executam seus scripts e podem ser encontradas por nome ou índice.
- Scripts de texto usam o mesmo ciclo de execução das outras propriedades, sem uma
  segunda cópia isolada que perdia importações e APIs do motor.
- Conversão de booleanos, números, strings e vetores de 2, 3 e 4 componentes. Strings
  como `bottom` não viram booleanos, e os componentes `z` e `w` são preservados.
- Ângulos expostos ao script em graus, com sincronização para os radianos do renderizador.
  Atribuição de vetores completos e alteração de componentes, como `angles.z`, são aceitas.
- `createScriptProperties` combina os valores declarados com as opções salvas da cena.
- `setTimeout`/`setInterval` mantêm as funções e a camada de origem vivas, permitem
  cancelamento dentro do próprio callback e liberam as referências ao terminar.
- `engine.canvasSize`, `userProperties`, indicadores de dispositivo/modo e buffers de áudio.
  `screenResolution` usa atualmente as dimensões da cena, não o tamanho físico do monitor.
- Criação de camadas de imagem, enumeração, ordenação e configuração inicial das
  camadas originais. `size`, `alignment`, `origin`, `scale` e `angles` alimentam a geometria.
- Texto: decodificação UTF-8, novas linhas explícitas, padding numérico, vetorial ou
  vinculado a script, tamanho rasterizado, fontes alteradas por script e alinhamento horizontal/vertical. Erros de
  tipo nas opções JSON propagam uma exceção tratável em vez de abortar via `noexcept`.
- Camadas mantêm identidade estável entre consultas e campos personalizados usados pelos scripts.
  Cores de camadas são expostas como RGB sem perder o alpha interno.
- Vetores: construtores parciais, enumeração de componentes, `dot` escalar,
  `lengthSqr` e ordem correta de `subtract`, `divide`, `cross` e `mix`.
- `getParent` e os 16 elementos `.m` de `getTransformMatrix`; a classe Mat4 completa
  ainda não está implementada.
- `getTextureAnimation`: `getFrame`, `setFrame`, `play`, `stop`, `rate`, `frameCount`
  e `playing`, com relógio individual de cada imagem e reprodução reversa.
- Cursor: coordenadas de cena e de tela e estado real do botão esquerdo. Eventos
  de entrada/saída/clique por camada ainda não são despachados.
- Scripts de camadas que falham durante o carregamento são removidos antes de
  liberar a camada; eles não podem executar sobre referências já destruídas.
- Emissores e operadores turbulence/vortex usam bandas de áudio e os limites e
  expoentes do autor. O espectro atual é mono; canais esquerdo/direito recebem
  a mesma análise, sem separação estéreo real.
- Texturas opcionais não definidas mantêm o recurso original do material.
  Propriedades de imagem aceitam arquivos locais decodificáveis pelo stb_image.

O [mapeamento do áudio e seus limites](AUDIO.md) é documentado separadamente.

## Lacunas conhecidas

As áreas abaixo ainda exigem implementação e testes de compatibilidade:

- Eventos de cursor por camada, atalhos do usuário e métodos adicionais de camadas.
- Animação esquelética/puppet e `getAnimationLayer`; formatos antigos MDLV0013–0019.
- Criação dinâmica de camadas que não sejam imagens, destruição dinâmica e APIs de parentesco.
- Controle de reprodução de camadas de som por scripts.
- Layout completo de texto: quebra automática de linhas, limites/reticências,
  fallback de fontes, efeitos e transformação completa por camadas parentes.
- Resolução real da saída, luzes/volume lights e renderização de cenas 3D com modelos.
- Persistência de localStorage e criação/destruição dinâmica de outros tipos de camada.

## Auditoria da biblioteca

A [bateria de 28/10/2026](engine-audit-2026-10-28.json) testou 19 cenas com buffers
de áudio: 17 renderizaram, 11 não registraram erros e nenhuma terminou com abort ou
segmentation fault. Duas ainda falharam com erro controlado durante o carregamento.
As cenas com erros de script ou efeitos ausentes não são classificadas como compatíveis
apenas por terem produzido um frame.

A bateria pode ser repetida com `tests/engine_library_audit.py`; passe `--engine`,
`--assets` e um diretório novo em `--output`, usando `DISPLAY=:99 PYTHONPATH=.`.

## Regressão nativa

Os testes não incluem arquivos de wallpapers de terceiros. O teste integrado recebe
um wallpaper de cena instalado para reutilizar seus recursos em uma cópia temporária,
sem modificar o original. Execute-o em um servidor X de teste, como Xvfb:

```sh
DISPLAY=:99 .venv/bin/python tests/engine_scenescript_smoke.py \
  --engine "$HOME/.local/bin/linux-wallpaperengine" \
  --wallpaper /caminho/do/wallpaper \
  --assets /caminho/do/wallpaper_engine/assets \
  --output /tmp/wpe-scenescript-smoke
```

Ele verifica o ciclo de vida, importações, grupos, valores padrão, vetores, mutação de
ângulos, buffers, texto, timers, cancelamento e tratamento de metadados inválidos.
O diretório de saída contém log e screenshot para inspeção.

Para o teste de conversão de valores vinculado ao motor compilado:

```sh
engine_src="$HOME/src/linux-wallpaperengine"
c++ -std=c++20 -I "$engine_src/src" -I "$engine_src/src/External/quickjs" \
  -I "$engine_src/src/External/json/include" tests/engine_script_values.cpp \
  -L "$engine_src/build/output" -Wl,-rpath,"$engine_src/build/output" \
  -llinux-wallpaperengine-lib -o /tmp/wpe-script-values-test
/tmp/wpe-script-values-test
```

Referências de interface: [IEngine](https://docs.wallpaperengine.io/en/scene/scenescript/reference/class/IEngine.html),
[ILayer](https://docs.wallpaperengine.io/en/scene/scenescript/reference/class/ILayer.html),
[IScene](https://docs.wallpaperengine.io/en/scene/scenescript/reference/class/IScene.html),
[WEVector](https://docs.wallpaperengine.io/en/scene/scenescript/reference/module/WEVector.html).

## Parâmetros e wallpapers web

A interface resolve presets (`dependency`/`preset`) e lê os tipos e padrões de
`project.json`. “Parâmetros do autor → Automático” não envia overrides; “Manual”
restaura os ajustes guardados. Os arquivos do Workshop não são alterados.
Propriedades `file`, `scenetexture` e `directory` podem ser editadas na interface.
Intensidade, curva e resposta do áudio mantêm seus controles independentes.

A ponte web injeta `wallpaperRegisterAudioListener` antes de executar a página,
entrega 128 valores (64 bandas mono repetidas para os dois canais) e chama
`applyUserProperties`/`applyGeneralProperties`. Inclui seleção aleatória em
propriedades de diretório. Integrações web de mídia/plugins e todos os callbacks
de diretório ainda não estão completos. Erros de JavaScript/carregamento são
registrados como `WebScript`/`WebLoad`.

Testes adicionais: `tests/engine_web_smoke.py` exige uma imagem verde produzida
pelos callbacks reais; `tests/engine_particle_audio.cpp` verifica bandas, silêncio,
limites e expoentes. `scripts/inventory-wallpapers.py --output /tmp/inventory.json`
inventaria a biblioteca sem alterar os originais. Os testes de renderização são
amostras curtas e não comprovam sincronização musical nem estabilidade prolongada.

## Varredura de 04/11/2026

Foram inspecionados 138 itens instalados: 94 cenas, 38 vídeos e 6 wallpapers web
(incluindo 2 presets com dependência). Há scripts em 43 itens; os módulos internos
importados são `WEMath`, `WEColor` e `WEVector`.

Os testes curtos produziram uma imagem para 137 itens, contra 128 antes das
correções. O item restante é uma cena 3D. Não houve abort/segmentation fault na
última rodada completa e nas rechecagens. Há erros de efeitos/scripts em parte das
cenas que renderizaram, portanto esse resultado não significa 137 itens plenamente
compatíveis. Permanecem as lacunas descritas acima, além de shaders de terceiros
que ainda precisam de compatibilidade específica.

Validação desta entrega: 75 testes Python, interface QML em automático/manual,
verificação dos 14 patches no commit fixado do motor, regressão SceneScript
(incluindo camada liberada após falha de shader e imagem PNG escolhida pelo usuário),
regressão web com cor produzida pelos callbacks e teste nativo da modulação de
partículas. Capturas de um ou poucos frames não validam efeitos ao longo da música.
