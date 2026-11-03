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

Os patches `0003`, `0004` e `0005` completam o caminho de áudio para os scripts:

- `engine.registerAudioBuffers(16|32|64)` fornece `Float32Array`s persistentes em `left`,
  `right` e `average`, atualizados antes de cada frame. Resoluções inválidas geram erro.
- O gravador atual captura uma mistura mono: os três canais recebem os mesmos valores.
- O patch `0005` captura PCM float de 32 bits em blocos de 10 ms, preservando
  detalhes baixos que desapareciam na quantização de 8 bits. Uma janela circular
  de 4096 amostras é analisada sempre que chegam dados, sem esperar outro bloco
  completo de aproximadamente 93 ms. A janela mantém essa duração; os resultados
  consecutivos se sobrepõem e continuam sujeitos à resolução temporal da FFT.
- A FFT a 44,1 kHz remove DC e aplica janela Hann. As 64 bandas cobrem 20 Hz–20 kHz
  em escala logarítmica. Bandas graves menores que um bin recebem interpolação
  entre bins vizinhos; isso evita lacunas, sem criar resolução de frequência nova.
- A reação combina a forma do espectro (75%) e o aumento de energia de cada banda
  entre análises (25%, fluxo espectral positivo). Uma referência comum se adapta
  ao nível ao longo do tempo, preservando diferenças entre frequências. Há um
  limite mínimo de referência e um gate de ruído; não é detecção de BPM nem
  separação de instrumentos. A intensidade regula a resposta; acima de 100%, uma compressão suave evita
  que todas as bandas fortes fiquem travadas no máximo.
- O movimento usa ataque de 18 ms e decaimento de 140 ms, calculados pelo tempo
  real entre frames. As resoluções de 32/16 bandas agrupam o pico depois da
  suavização. Sem dados novos por 150 ms, o espectro decai até zero.
- Essa distribuição e resposta são políticas do motor Linux, não uma reprodução
  exata do processamento interno do Wallpaper Engine para Windows.
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

Testar captura, resposta por frequência, ataques e consistência entre FPS:

```sh
c++ -std=c++20 -I "$engine_src/src" tests/engine_audio_dynamics.cpp -o /tmp/wpe-audio-dynamics-test
/tmp/wpe-audio-dynamics-test
```

## Resposta rápida e referências (patch 0006)

O patch `0006` substitui a janela única de 4096 amostras por duas janelas
sobrepostas: 2048 amostras para graves e 1024 para médios/agudos. As potências são
combinadas com uma transição entre 120 e 300 Hz antes da normalização. Há menos
resolução nos subgraves do que na janela anterior; interpolação não substitui
resolução real. Os limites de 20 Hz–20 kHz e os buffers 16/32/64 são preservados.

A captura solicita fragmentos de 5 ms, limita a fila a 40 ms e usa ataque de
6 ms e queda de 100 ms. São parâmetros internos, não uma garantia de latência
fim a fim: o servidor de áudio, o FPS e os filtros do wallpaper também contam.

O teste `tests/engine_audio_latency.cpp` mede o tempo até 25% da potência de um
tom sintético, com passos de cerca de 5 ms. Nesta implementação, passou de
49,9 para 24,9 ms em 86,1 Hz, e de 49,9 para 15,0 ms em 1378,1 Hz. Ele não mede
sincronia audiovisual na tela nem reconhecimento de instrumentos em músicas.
Compile com as mesmas opções de `tests/engine_spectrum.cpp`, trocando o nome do
arquivo e do executável.

Referências consultadas em 3 de novembro de 2026:

- [Wallpaper Engine: processamento com SceneScript](https://docs.wallpaperengine.io/en/scene/scenescript/tutorial/audio.html)
  documenta a seleção de bandas e a suavização no próprio script, usando o tempo
  entre frames. Não publica nesse tutorial o algoritmo interno completo da FFT.
- [Wallpaper Engine: AudioBuffers](https://docs.wallpaperengine.io/en/scene/scenescript/reference/class/AudioBuffers.html)
  descreve buffers de canais esquerdo/direito e média, atualizados por frame.
  O motor deste projeto ainda captura mono; não há separação estéreo real.
- [CAVA: implementação de análise](https://github.com/karlstav/cava/blob/master/cavacore.c)
  usa uma janela maior para graves, outra para médios/agudos, ganho por frequência,
  sensibilidade automática e filtros de queda. A implementação aqui é própria;
  não reproduz exatamente a distribuição ou os filtros do CAVA.
- [projectM](https://github.com/projectM-visualizer/projectm)
  combina FFT com detecção de batidas para alimentar a visualização.

O resultado final também depende do autor do wallpaper. Um efeito que lê só as
bandas graves não acompanha um solo apenas porque o motor captura médios/agudos.
Alterar essa intenção deve ser um ajuste explícito do wallpaper/perfil, mantendo
as frequências independentes. Análise espectral não isola automaticamente guitarra,
voz, baixo ou bateria de uma mixagem.

## Sincronização por wallpaper (patch 0008)

O painel procura propriedades numéricas expostas pelo wallpaper com nomes/rótulos
relacionados a áudio e tempo de resposta (por exemplo, `Audio Smooth Delay`).
Quando encontra um controle, mantém a propriedade nativa disponível na lista
normal e não exibe um substituto. Essa detecção é conservadora, baseada nos
metadados expostos em `project.json`; filtros internos de shaders/scripts que o
autor não expõe não são reinterpretados nem alterados automaticamente.

Sem controle nativo reconhecido, wallpapers reativos oferecem:

- **Automático**: acelera a subida em ataques abruptos, solta quedas fortes e
  suaviza notas sustentadas. Não detecta BPM nem antecipa som ainda não capturado.
- **Manual**: velocidade entre 25% e 400%; 100% usa ataque de 6 ms e queda de
  100 ms. O multiplicador divide ambos os tempos, sem mudar a faixa de frequências.

O ajuste é independente por wallpaper. A interface grava um pequeno valor de
controle atomicamente em `~/.local/state/wpe-gui/audio-controls/` (respeitando
`XDG_STATE_HOME`), e passa seu caminho com `WPE_AUDIO_RESPONSE_FILE`. O motor
consulta o arquivo a cada 100 ms. Valores inválidos mantêm o último ajuste válido.
Alterar somente o modo/velocidade atualiza a resposta sem recriar os processos
nem disparar uma nova captura do fundo estático. O modo automático usa o valor
0 no arquivo; o manual usa multiplicadores de 0,25 a 4.

Isso regula a resposta do espectro. Atrasos adicionais inseridos pelo próprio
wallpaper, pelo servidor de áudio ou pelo FPS não são removidos automaticamente.

## Curva do espectro (patch 0009)

**Curva do espectro** tem modos independentes da velocidade de sincronização:

- **Automático** mantém a transferência do motor neutra (fator 1), preservando a
  curva aplicada pelos shaders/scripts do wallpaper. Quando há propriedade
  numérica exposta de curva/expoente/gamma do áudio, o painel a identifica e
  mantém o controle nativo nas propriedades. Sem ela, usa a resposta padrão;
  não tenta deduzir valores de controles genéricos de brilho ou velocidade.
- **Manual** aceita 25%–400%. A transferência é `y = x^(1/fator)` para níveis
  normalizados de 0 a 1: 100% é identidade, abaixo reduz níveis intermediários e
  acima os realça. Silêncio continua zero e o máximo continua um. Isso muda a
  forma da resposta, separadamente de volume, intensidade e velocidade.

O fator manual é guardado por wallpaper. Voltar ao automático usa fator 1 sem
apagar o valor manual salvo nem alterar os arquivos/propriedades do wallpaper.
As curvas internas continuam sendo aplicadas também no modo manual; o controle
é uma transformação adicional do espectro, não uma edição do shader do autor.

O fator é enviado em arquivo escalar próprio, indicado por
`WPE_AUDIO_CURVE_FILE`, e atualizado ao vivo a cada 100 ms. Não recria a cena nem
provoca captura do fundo. A detecção de controles nativos depende dos nomes e
rótulos numéricos expostos, sem prometer reconhecer todo controle personalizado.
