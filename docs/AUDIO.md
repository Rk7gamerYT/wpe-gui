# Áudio dos wallpapers

O volume e o silenciamento globais ficam em Configurações. No painel de ajustes de cada
wallpaper, **Som do wallpaper** permite seguir o padrão, ligar o som ou silenciar;
**Volume do wallpaper** permite sobrescrever o volume global. O botão **Padrão** remove
essa sobrescrita. A escolha vale para todas as telas que exibem o mesmo wallpaper.
Wallpapers diferentes podem reproduzir áudio em cada monitor. Quando o mesmo
wallpaper aparece em várias telas, apenas uma cópia reproduz o som, evitando eco
e volume duplicado. Uma cópia não pausada assume o áudio se a fonte anterior for
pausada ou fechada; a captura do espectro continua ativa nas demais cópias. Mudanças de áudio reiniciam os processos afetados após um pequeno atraso,
preservando a pausa do modo economia.

**Intensidade do áudio** controla a reação ao som capturado, separadamente do volume de
reprodução. Silenciar um wallpaper não desliga o espectro da música tocada por outros apps.

## Motor e SceneScript

Os patches `0003` e `0004` completam o caminho de áudio para os scripts:

- `engine.registerAudioBuffers(16|32|64)` fornece `Float32Array`s persistentes em `left`,
  `right` e `average`, atualizados antes de cada frame. Resoluções inválidas geram erro.
- O gravador atual captura uma mistura mono: os três canais recebem os mesmos valores.
- A FFT usa 4096 amostras a 44,1 kHz, remove DC e aplica janela Hann. As 64 bandas
  cobrem 20 Hz–20 kHz em escala logarítmica; as resoluções menores agrupam bandas
  adjacentes pelo pico. O nível é normalizado entre −60 e 0 dBFS, multiplicado pela
  intensidade e limitado a 0–1. Intensidade zero deixa todas as bandas em zero.
- Essa distribuição de frequências é uma política explícita do motor Linux; a
  documentação pública do Wallpaper Engine não especifica seus limites exatos por banda.
- Scripts passam a executar seus módulos, `init` e `update`, com o contexto da camada
  correspondente. Vetores e escrita de propriedades alimentam a geometria renderizada.
  Ângulos do SceneScript são convertidos de graus para radianos usados pelo renderizador.
- Camadas de imagem podem ser criadas por caminho ou configuração, listadas e reordenadas.
  `getInitialLayerConfig` aceita referências de camadas originais; criação dinâmica de
  outros tipos e controle de reprodução de camadas de som ainda não estão completos.
  `registerAsset` mantém o caminho como identificador de um recurso já instalado.
- O app detecta shaders e scripts de áudio mesmo sem a declaração no `project.json` e
  sinaliza `WPE_AUDIO_PROCESSING=1` ao motor. A opção `--no-audio-processing` ainda prevalece.

Referências: [buffers de áudio](https://docs.wallpaperengine.io/en/scene/scenescript/reference/class/AudioBuffers.html),
[API do motor](https://docs.wallpaperengine.io/en/scene/scenescript/reference/class/IEngine.html),
[camadas](https://docs.wallpaperengine.io/en/scene/scenescript/reference/class/ILayer.html).

A cobertura geral e as lacunas de scripts estão em [Compatibilidade SceneScript](SCENESCRIPT.md).

## Verificação

Testes do app:

```sh
.venv/bin/python -m unittest discover -s tests
```

Teste nativo do mapeamento (ajuste `engine_src` para a pasta do motor compilado):

```sh
engine_src="$HOME/src/linux-wallpaperengine"
c++ -std=c++20 -I "$engine_src/src" -I "$engine_src/src/External/kissfft" \
  tests/engine_spectrum.cpp -L "$engine_src/build/lib" \
  -Wl,-rpath,"$engine_src/build/lib" -lkissfft-float -o /tmp/wpe-spectrum-test
/tmp/wpe-spectrum-test
```

O teste usa tons sintéticos próximos de 65 Hz, 1 kHz e 10 kHz, verifica os picos nas
64/32/16 bandas e verifica rejeição de DC e valores não finitos.

## Pausa manual

Na barra inferior, **Pausar todos** aplica uma pausa global. **Retomar todos** remove
as pausas manuais, preservando as pausas automáticas do modo economia. O menu
**Monitores** permite pausar ou retomar uma tela específica. Os mesmos controles
estão no menu do ícone da bandeja.

É possível retomar uma tela durante a pausa global: as outras continuam pausadas.
As pausas manuais são mantidas durante alterações de propriedades, redistribuição
de áudio e reinícios do motor na sessão atual. A opção **Parar** encerra os processos
e limpa a pausa manual. No modo estendido há um único processo para todas as telas;
por isso o menu mostra um único alvo, **Todos os monitores (estendido)**.
