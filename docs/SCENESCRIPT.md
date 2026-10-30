# Compatibilidade SceneScript no fork

O motor está em desenvolvimento. Renderizar uma imagem não comprova que todos os scripts,
efeitos e interações do wallpaper estejam funcionando. A bateria de integração verifica
as funções de forma explícita e a auditoria da biblioteca registra as falhas restantes.

## Base implementada e testada

- Módulos ES, incluindo importações de `WEMath`, `WEColor`, `WEVector` e arquivos JS do
  próprio wallpaper. Módulos desconhecidos geram erros identificando o nome.
- Avaliação dos scripts após criar o grafo de camadas; `init` em ordem de criação e
  dependências, antes de executar `update`. `destroy` roda antes de liberar as camadas.
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
- Metadados de texto aceitam padding numérico ou dois componentes em texto. Erros de
  tipo nas opções JSON propagam uma exceção tratável em vez de abortar via `noexcept`.

O [mapeamento do áudio e seus limites](AUDIO.md) é documentado separadamente.

## Lacunas conhecidas

As áreas abaixo ainda exigem implementação e testes de compatibilidade:

- Eventos de cursor e botões; entrada em coordenadas de mundo.
- Controle de animações por SceneScript e métodos adicionais de camadas.
- Criação dinâmica de camadas que não sejam imagens, destruição dinâmica e APIs de parentesco.
- Controle de reprodução de camadas de som por scripts.
- Layout completo de texto, caracteres Unicode, quebra de linhas, limites e aplicação
  visual de padding. O valor é preservado, mas o rasterizador ainda tem limitações.
- Resolução real da saída, renderização completa de luzes e volume lights e modulação
  de áudio em emissores/operadores de partículas.

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
