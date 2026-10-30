# Instalação

## Opção recomendada: AppImage

Use o [pacote completo da última release](https://github.com/Rk7gamerYT/wpe-gui/releases/latest).
Ele inclui o app, o motor e as bibliotecas. As dependências e a compilação das seções
seguintes são necessárias apenas para instalar pelo código-fonte.
Veja os requisitos e o atualizador integrado nas [notas da versão](RELEASE.md).


O **wpe-gui** é só a interface. Para funcionar você precisa de três coisas:

1. o **motor** [linux-wallpaperengine](https://github.com/Almamu/linux-wallpaperengine), compilado com os patches deste projeto;
2. o **Wallpaper Engine do Steam** instalado (os wallpapers e os assets vêm dele, o projeto não os inclui);
3. o próprio app e a integração do ambiente: extensão GNOME ou plugin Plasma e extensão KWin no KDE.

> **O que foi testado.** Testado no **Ubuntu 26.04 com GNOME 50 e com KDE Plasma 6, em Wayland**. As listas de pacotes do
> Fedora e do Arch vêm do README do motor e **não foram testadas pelo autor**. Se algo falhar, abra uma issue com a saída do erro.

## Sumário

- [KDE no Ubuntu 26.04: guia completo](KDE-UBUNTU-26.04.md)
- [Instalação rápida (script)](#instalação-rápida-script)
- [Passo a passo por distro](#passo-a-passo-por-distro)
  - [Ubuntu, Debian, Linux Mint, Pop!_OS](#ubuntu-debian-linux-mint-pop_os)
  - [Fedora](#fedora)
  - [Arch, Manjaro, EndeavourOS](#arch-manjaro-endeavouros)
  - [Outras distros](#outras-distros)
- [Compilar o motor com os patches](#compilar-o-motor-com-os-patches)
- [Instalar o app](#instalar-o-app)
- [Wallpaper Engine no Steam](#wallpaper-engine-no-steam)
- [Ambiente gráfico](#ambiente-gráfico)
- [Primeiro uso](#primeiro-uso)
- [Problemas comuns](#problemas-comuns)
- [Atualizar e desinstalar](#atualizar-e-desinstalar)

## Instalação rápida (script)

Um comando instala o app, o motor com os patches e a integração do ambiente:

```bash
curl -fsSL https://raw.githubusercontent.com/Rk7gamerYT/wpe-gui/main/install-online.sh | bash
```

Execute como seu usuário normal, sem `sudo` antes do comando. A senha é solicitada
para instalar os pacotes. Não é necessário clonar o repositório, configurar o
caminho do motor nem alterar o `PATH`. Ao concluir, abra **Wallpaper Engine** pelo menu.
O mesmo comando atualiza uma instalação feita por ele; encerre o app antes de atualizar.

O código fica em `~/.local/share/wpe-gui/app` e o motor em
`~/.local/share/wpe-gui/linux-wallpaperengine`. Um diretório de dados XDG personalizado
altera o local do app. O instalador verifica se o motor executa e salva seu caminho
absoluto, preservando as preferências e os wallpapers salvos.
O log fica em `~/.local/state/wpe-gui/install.log` (ou em `$XDG_STATE_HOME/wpe-gui/install.log`).

Para quem prefere trabalhar com o código:

```bash
git clone https://github.com/Rk7gamerYT/wpe-gui.git
cd wpe-gui
./install.sh --dry-run
./install.sh
```

O script reconhece Ubuntu/Debian e derivadas, Fedora e Arch e derivadas. Ele:

1. instala os pacotes do sistema com `sudo` (é o único passo que pede a senha);
2. baixa o motor na versão certa, aplica os patches e compila, **com poucos jobs de propósito** (cerca de 2 GB de memória
   por job), para não travar o computador;
3. instala o app, o ícone e a entrada no menu de aplicativos;
4. detecta a sessão atual: no GNOME instala a extensão; no KDE instala o plugin Plasma e a extensão KWin.

Opções: `--yes` (não perguntar), `--no-deps` (você já tem os pacotes), `--no-engine` (você já tem o motor com os patches),
`--no-gnome` e `--no-kde`. Depois, falta só o [Wallpaper Engine no Steam](#wallpaper-engine-no-steam).

## Passo a passo por distro

Cada distro tem só o primeiro passo diferente: instalar as dependências. O resto é igual.

### Ubuntu, Debian, Linux Mint, Pop!\_OS

*Testado no Ubuntu 26.04.* No Ubuntu 22.04 troque `libmpv2` por `libmpv1`.

```bash
sudo apt-get update
sudo apt-get install -y build-essential cmake git pkg-config \
  libxrandr-dev libxinerama-dev libxcursor-dev libxi-dev libgl-dev libglew-dev freeglut3-dev \
  libsdl2-dev liblz4-dev libavcodec-dev libavformat-dev libavutil-dev libswscale-dev \
  libxxf86vm-dev libglm-dev libglfw3-dev libmpv-dev mpv libmpv2 libpulse-dev libpulse0 \
  libfftw3-dev libfreetype-dev libwayland-dev wayland-protocols libxkbcommon-dev \
  python3 python3-venv python3-pip ffmpeg x11-utils
```

### Fedora

*Lista adaptada do README do motor (Fedora 42). Não testada pelo autor.*

```bash
sudo dnf install -y gcc gcc-c++ cmake git \
  libXrandr-devel libXinerama-devel libXcursor-devel libXi-devel mesa-libGL-devel glew-devel freeglut-devel \
  SDL2-devel lz4-devel ffmpeg-free ffmpeg-free-devel libXxf86vm-devel glm-devel glfw-devel mpv mpv-devel \
  pulseaudio-libs-devel fftw-devel gmp-devel freetype-devel wayland-devel wayland-protocols-devel \
  libxkbcommon-devel python3 python3-pip xorg-x11-utils
```

Para decodificar todos os vídeos você provavelmente precisa do `ffmpeg` completo do
[RPM Fusion](https://rpmfusion.org/); o `ffmpeg-free` não tem todos os codecs.

### Arch, Manjaro, EndeavourOS

*Lista montada a partir do README do motor (que só cita o AUR). Não testada pelo autor.*

```bash
sudo pacman -S --needed base-devel cmake git libxrandr libxinerama libxcursor libxi mesa glew freeglut sdl2-compat lz4 \
  ffmpeg libxxf86vm glm glfw mpv libpulse fftw freetype2 wayland wayland-protocols libxkbcommon \
  python python-pip xorg-xprop xorg-xwininfo
```

O pacote `linux-wallpaperengine-git` do AUR instala o motor, mas **sem os patches deste projeto**: o app funciona, porém
wallpapers que usam vetores de tamanhos diferentes no shader ficam pretos e a "Intensidade do áudio" não tem efeito.
Para ter tudo, compile o motor como abaixo.

### Outras distros

Instale, com os nomes que sua distro usar: um compilador C++, `cmake`, `git`, Python 3 com `venv`, `ffmpeg`, `xprop` e
`xwininfo`, e as bibliotecas de desenvolvimento de **X11 (Xrandr, Xinerama, Xcursor, Xi, Xxf86vm), OpenGL, GLEW, freeglut,
SDL2, GLFW, GLM, lz4, FFmpeg (avcodec, avformat, avutil, swscale), libmpv, PulseAudio, FFTW, FreeType, Wayland e xkbcommon**.
Depois siga os passos seguintes. Se faltar algo, o `cmake` diz o nome da biblioteca.

## Compilar o motor com os patches

O projeto traz dois patches, em `patches/`, feitos sobre uma versão específica do motor (por isso o passo `checkout`):

| Patch | O que faz |
|---|---|
| `0001-shaders-repair-implicit-vector-truncation.patch` | O compilador de shaders do Windows aceita `vec4 * vec2` (corta o vetor maior); o GLSL não. Sem o patch, wallpapers que fazem isso ficam **pretos**. |
| `0002-audio-add-audio-gain-option.patch` | Adiciona `--audio-gain`, usado pela "Intensidade do áudio". |
| `0003-scripting-audio-buffers-and-layers.patch` | Entrega o espectro ao SceneScript e executa os scripts das barras e camadas. |
| `0004-audio-map-spectrum-frequency-bands.patch` | Corrige a distribuição das frequências e o agrupamento das bandas de áudio. |

```bash
git clone --recurse-submodules https://github.com/Almamu/linux-wallpaperengine.git
cd linux-wallpaperengine
git checkout b016d7d1fdcf4e5fd2f9c9fa420a8aaa07fee02d
git submodule update --init --recursive
git apply /caminho/para/wpe-gui/patches/0001-*.patch /caminho/para/wpe-gui/patches/0002-*.patch

mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=Release ..
nice make -j3        # veja o aviso abaixo
```

> **Cuidado com a memória.** Compilar com `make -j$(nproc)` usa muita RAM (cerca de 2 GB por job) e **pode travar o
> computador**. Use no máximo `memória livre em GB ÷ 2` jobs, por exemplo `-j3` com 8 GB livres. O `cmake` também baixa
> o CEF (o navegador embutido, algumas centenas de MB), então precisa de internet e de espaço em disco.

Deixe o executável no seu `PATH`:

```bash
mkdir -p ~/.local/bin
ln -sf "$PWD/output/linux-wallpaperengine" ~/.local/bin/linux-wallpaperengine
linux-wallpaperengine --help | head -3     # tem que funcionar de qualquer pasta
```

Se o `~/.local/bin` não estiver no `PATH`, adicione `export PATH="$HOME/.local/bin:$PATH"` ao `~/.profile`.

## Instalar o app

```bash
cd /caminho/para/wpe-gui
./wpe-gui.sh --install-desktop    # ícone e entrada no menu de aplicativos (só no seu usuário)
./wpe-gui.sh                      # abre o app (na primeira vez cria o ambiente Python)
```

Para abrir de qualquer terminal: `ln -s "$PWD/wpe-gui.sh" ~/.local/bin/wpe-gui`.
`./wpe-gui.sh --uninstall-desktop` remove o ícone e a entrada do menu.

## Wallpaper Engine no Steam

O motor lê os wallpapers e os arquivos de assets do **Wallpaper Engine do Steam** (app 431960, pago). O projeto não inclui nada disso.

1. Tenha o Wallpaper Engine na sua conta Steam.
2. No Steam do Linux, ative o Steam Play, para ele deixar baixar um programa feito para Windows:
   *Steam → Configurações → Compatibilidade → Ativar o Steam Play para todos os outros títulos*.
3. Instale o Wallpaper Engine pelo Steam. Você **não precisa executá-lo**; só precisa dos arquivos.
4. Inscreva-se nos wallpapers que quiser na Oficina (Workshop) do Steam. Eles são baixados para
   `steamapps/workshop/content/431960/`.

O app encontra sozinho as bibliotecas do Steam, inclusive as em outros discos montados (em `/mnt`, `/media` e
`/run/media`). Se a sua estiver em outro lugar, aponte as pastas em **Configurações**.
Se o disco com o Steam for NTFS (de um Windows), monte-o com o driver `ntfs3`; se ele não montar, desligue a
"Inicialização rápida" do Windows (ela deixa o disco marcado como em uso).

## Ambiente gráfico

### KDE Plasma 6 (Wayland) — testado no Ubuntu 26.04

Veja o [passo a passo completo para KDE no Ubuntu 26.04](KDE-UBUNTU-26.04.md),
incluindo instalar o KDE ao lado do GNOME, instalar o app e solucionar fundo preto.

Se já estiver na sessão Plasma:

```bash
./install.sh
./wpe-gui.sh
```

O instalador detecta o KDE. Para um app e motor já instalados, basta `./kde/install.sh`.
O app seleciona o modo Wayland nativo automaticamente, preserva ícones e widgets,
restaura as atribuições por monitor e carrega a extensão KWin para pausar o wallpaper
nos monitores cobertos por uma janela maximizada ou em tela cheia.

### GNOME (Wayland) — testado no Ubuntu 26.04

O GNOME não oferece o protocolo que os outros ambientes usam para fixar um programa no fundo da tela (`layer-shell`).
Por isso, no GNOME:

1. Em **Configurações → modo janela**, deixe ligado (o app roda o motor pelo XWayland, porque o GLEW não inicia no Wayland nativo).
2. Instale a extensão, que move a janela do motor para a camada de fundo:

   ```bash
   ./extension/install.sh
   ```

   Depois **saia da sessão e entre de novo**. Confira com `gnome-extensions info wpe-background@wpe-gui` (deve mostrar `ACTIVE`).

   A extensão declara suporte ao GNOME **48 a 50** e foi testada no 50. Em versões mais antigas (por exemplo o Ubuntu 24.04,
   que usa o GNOME 46) o GNOME a recusa; editar `shell-version` no `metadata.json` por sua conta é possível, mas não foi testado.
3. Para o ícone da **bandeja do sistema**, é preciso a extensão *AppIndicator*. No Ubuntu ela já vem ativa. No Fedora e no Arch:
   instale `gnome-shell-extension-appindicator` e ative-a (`gnome-extensions enable appindicatorsupport@rgcjonas.gmail.com`).
   Sem bandeja, fechar a janela encerra o app.

### Sessão X11

Deve funcionar com o modo janela, pois o app marca a janela do motor como "desktop" e a deixa transparente para cliques.
A extensão do GNOME não se aplica. **Não foi testado pelo autor.**

### Hyprland, Sway e outros com `layer-shell`

O motor tem o modo `--screen-root` (fixa o wallpaper no fundo sem precisar de janela). Nesses ambientes, **desligue o "modo janela"**
nas configurações. **Não foi testado pelo autor.** A extensão do GNOME não se aplica.

## Primeiro uso

1. Abra o app. A grade lista os wallpapers do Steam encontrados.
2. Clique em um wallpaper e em **Aplicar**. Com vários monitores, a seta ao lado escolhe só um deles.
3. Ajuste o que quiser no painel da direita (propriedades, escala, intensidade do áudio).
4. Feche a janela: o app continua na bandeja. Clique no ícone para abrir de novo.

Dica: para o app subir sozinho e silencioso, como o Steam, ligue **Iniciar escondido na bandeja** nas configurações e
ligue **Iniciar com o sistema** no próprio app. A opção **Restaurar wallpapers ao abrir o app**
reaplica os wallpapers salvos ao iniciar a sessão.

## Problemas comuns

| Sintoma | Causa e solução |
|---|---|
| O computador trava ao compilar o motor | Jobs demais. Use `make -j2` ou `-j3`. No Ubuntu, o `systemd-oomd` derruba a sessão sob pressão de memória; ter *zram*/swap maior ajuda. |
| KDE: wallpaper some quando aparecem ícones | Atualize com `./kde/install.sh` e reinicie o Plasma: `systemctl --user restart plasma-plasmashell.service`. O plugin precisa deixar transparente também a janela dos ícones. |
| KDE: pausa automática não funciona | Veja a verificação da extensão KWin no [guia KDE](KDE-UBUNTU-26.04.md#verificar-a-integração). |
| Wallpaper fica **preto** | Provavelmente o patch de shaders não está no motor. Confira com `linux-wallpaperengine --help \| grep audio-gain` (se não aparecer, o motor está sem os patches). |
| O app não encontra o motor | Execute novamente o instalador completo. Ele verifica o executável e configura o caminho automaticamente. O app também procura em `~/.local/bin`, mesmo quando a sessão não inclui essa pasta no `PATH`. |
| O motor fecha na hora | Rode o mesmo comando do app na mão para ver o erro. Um clássico é `pattern '100.0' does not match` (versões antigas do app). |
| `Failed to initialize GLEW` | No GNOME, use o **modo janela**. No KDE, o aviso pode ser seguido de `continuing with EGL context`: se o wallpaper renderiza, não é uma falha fatal. |
| Wallpaper aparece **por cima** das janelas | A extensão do GNOME não está carregada. Saia e entre na sessão e confira `gnome-extensions info wpe-background@wpe-gui`. |
| Apps X11 (Steam, xterm...) não respondem a cliques | Corrigido no app atual: atualize (`git pull`) e reinicie o app. |
| Sem som no wallpaper | Desligue "Silenciar quando outro app tocar áudio". Com vários monitores só um wallpaper toca (o do monitor principal). |
| Engrenagem no dock / sem ícone | Rode `./wpe-gui.sh --install-desktop` e reabra o app. |
| Sem ícone na bandeja | Instale/ative a extensão AppIndicator (veja acima). |
| O app não acha os wallpapers | Confira se o Wallpaper Engine está instalado e se há wallpapers em `steamapps/workshop/content/431960/`; ou aponte a pasta em Configurações. |

## Atualizar e desinstalar

**Atualizar instalação pelo comando único:**

Encerre o app pela bandeja e execute novamente o comando da instalação rápida.
Se o instalador solicitar recarregar o Plasma, use o comando indicado.

**Atualizar um clone Git:**

```bash
cd /caminho/para/wpe-gui
git pull --ff-only
./install.sh --no-deps     # recompila o motor se os patches mudaram e atualiza a extensão
```

Depois reinicie o app. No GNOME, se a extensão mudou, saia e entre na sessão.
No KDE, se o plugin mudou, reinicie o Plasma com
`systemctl --user restart plasma-plasmashell.service` antes de reabrir o app.

**Desinstalar:**

```bash
./wpe-gui.sh --uninstall-desktop
gnome-extensions uninstall wpe-background@wpe-gui   # só no GNOME
# Só no KDE, após restaurar o fundo anterior e encerrar o app:
rm -rf ~/.local/share/plasma/wallpapers/org.wpegui.wallpaper ~/.local/share/kwin/scripts/wpe-gui
rm -f ~/.local/bin/linux-wallpaperengine ~/.local/bin/wpe-gui
rm -rf ~/.local/share/wpe-gui ~/.config/wpe-gui      # motor compilado, imagens geradas e configurações
```

Se o app trocou o fundo do sistema (função "Fundo estático"), use **Configurações → Restaurar o fundo de antes** *antes* de apagar a pasta de configurações.
