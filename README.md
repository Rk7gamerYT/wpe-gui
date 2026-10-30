# wpe-gui

## Download do pacote completo

Baixe o **AppImage x86_64** em [Releases](https://github.com/Rk7gamerYT/wpe-gui/releases/latest).
Um único arquivo inclui a interface, Python, Qt, o motor corrigido e suas bibliotecas.
Permita a execução do arquivo e abra-o. Não é preciso instalar dependências ou compilar.
Requer glibc 2.39+ (Ubuntu 24.04+, Debian 13 e distros atuais) e drivers gráficos do desktop.
Os wallpapers/assets comerciais continuam vindo do Wallpaper Engine instalado pelo Steam.

O atualizador fica em **Configurações → Atualizações** e verifica o SHA-256 antes de
substituir o AppImage. No KDE, o plugin e a extensão KWin já estão dentro do pacote.

As instruções abaixo para compilação são destinadas ao desenvolvimento/instalação pelo código-fonte.


Interface gráfica (Qt6/QML) para o [linux-wallpaperengine](https://github.com/Almamu/linux-wallpaperengine), com layout inspirado no Wallpaper Engine do Windows: grade de wallpapers, painel de preview à direita e página de configurações.

> Este projeto **não** inclui o motor nem os wallpapers. Você precisa do `linux-wallpaperengine` instalado e de uma cópia do Wallpaper Engine na Steam.

## Instalação

**Copie e cole este único comando no terminal, sem sudo:**

```bash
curl -fsSL https://raw.githubusercontent.com/Rk7gamerYT/wpe-gui/main/install-online.sh | bash
```

Ele baixa o app, instala as dependências, compila o motor com os patches, configura
seu caminho e instala a integração KDE/GNOME. Depois, abra **Wallpaper Engine** pelo
menu de aplicativos. A compilação leva alguns minutos e solicita sua senha para instalar pacotes.
Você ainda precisa ter o Wallpaper Engine instalado pela Steam e baixar os wallpapers pela Oficina.

Para atualizar, encerre o app pela bandeja e execute o mesmo comando novamente.
O app fica em `~/.local/share/wpe-gui/app`; suas preferências são preservadas.
O log da instalação fica em `~/.local/state/wpe-gui/install.log`.

Se já baixou o código, `./install.sh` também instala tudo. Para conferir os comandos
sem instalar, use `./install.sh --dry-run`.

Guia por distro: **[docs/INSTALL.md](docs/INSTALL.md)**.
Para **Ubuntu 26.04 com KDE Plasma**, veja o [passo a passo dedicado](docs/KDE-UBUNTU-26.04.md).

## Status

Versão inicial (0.1). Já faz:

- Lista wallpapers instalados pela Steam (`steamapps/workshop/content/431960`) e pastas extras
- Busca e filtro por tipo
- Aplica/para o wallpaper (duplo clique ou botão), com **um wallpaper por monitor**, o mesmo **duplicado** em todos ou **esticado** entre eles
- Ajustes por wallpaper: escala, bordas e as propriedades do próprio wallpaper (sliders, cores, listas...)
- Salva configurações e monitores em `~/.config/wpe-gui/settings.json` e ajustes por wallpaper em `~/.config/wpe-gui/overrides.json`, com gravação atômica
- Restaura os wallpapers ao abrir o app ou pelo botão **Restaurar wallpapers** na janela e na bandeja; **Parar** preserva o último conjunto salvo
- **Modo economia:** pausa o wallpaper só no monitor que tiver um app em tela cheia ou maximizado (pelas extensões GNOME ou KWin no KDE)
- **Bandeja do sistema:** fechar a janela mantém o app e os wallpapers rodando; o ícone abre a interface de novo (há a opção "Iniciar escondido na bandeja") (no GNOME, usa a extensão AppIndicator, já ativa no Ubuntu)
- **Fundo estático:** ao fechar o app, o desktop fica com uma imagem do wallpaper em vez de voltar ao fundo antigo (GNOME e KDE Plasma/Wayland)
- **Intensidade do áudio:** global e por wallpaper, para os que reagem ao som
- Configurações: FPS, volume, mudo, escala, pausa em tela cheia, modo janela

Em Configurações, **Iniciar com o sistema** abre o app ao entrar na sessão do usuário. Mantenha **Restaurar wallpapers ao abrir o app** ligado para reaplicar os wallpapers salvos. Desligar a inicialização automática remove a entrada de autostart.

Planejado: playlists e integração com o Workshop.

### Imagem na tela de login (Ubuntu/GDM)

Depois de aplicar um wallpaper, use **Usar imagem na tela de login** no painel dele.
O app reinicia brevemente um monitor para capturar a cena com as propriedades atuais,
sem janelas ou ícones, e pede autenticação de administrador para instalar a imagem
estática no GDM. A animação continua sendo executada apenas após entrar na conta.
O recurso utiliza a configuração nativa `com.ubuntu.login-screen` do Ubuntu; não
modifica o tema nem reinicia o GDM ou encerra sua sessão.

A imagem fica em `/var/lib/wpe-gui/login.png`, acessível antes do login, e a
configuração em `/usr/share/gdm/dconf/99-wpe-gui`. Para remover a personalização,
use **Restaurar o fundo de antes** nas configurações. A mudança vale para a tela de
login do sistema, compartilhada entre os usuários; não altera a tela de bloqueio.

## Executar

```bash
./wpe-gui.sh
```

Para ter o ícone e a entrada no menu de aplicativos (o dock deixa de mostrar uma engrenagem), rode uma vez `./wpe-gui.sh --install-desktop`; `--uninstall-desktop` remove. Com `--minimized` o app inicia só na bandeja.

Na primeira vez o script cria o ambiente Python (`.venv`) e instala a dependência sozinho. Para abrir de qualquer pasta, crie um link no seu `PATH`:

```bash
ln -s "$PWD/wpe-gui.sh" ~/.local/bin/wpe-gui
```

## Motor com correções

Duas funções dependem de patches no `linux-wallpaperengine`, em `patches/` (feitos sobre uma versão fixa do motor; o `install.sh` e o [guia de instalação](docs/INSTALL.md) já cuidam disso):

- **`0001` — reparo de vetores nos shaders:** o compilador do Windows aceita `vec4 * vec2` (corta o vetor maior) e o GLSL não. Sem o patch, wallpapers que fazem isso ficam pretos.
- **`0002` — `--audio-gain`:** multiplica o espectro de áudio que os wallpapers recebem; é o que a "Intensidade do áudio" usa.

Com o motor sem os patches, o app funciona, mas esses dois recursos não têm efeito.

## KDE Plasma 6 (Wayland)

Instale o plugin de wallpaper do Plasma e a extensão do KWin, sem sudo:

```bash
./kde/install.sh
./wpe-gui.sh
```

O app usa automaticamente o modo Wayland nativo no KDE, mesmo se o modo janela
ficou salvo de uma sessão GNOME. O plugin **Wallpaper Engine (wpe-gui)** mantém
o desktop transparente sobre a animação, preservando os ícones, widgets e painéis.
No botão direito da área de trabalho, **Mostrar ícones da área de trabalho**
alterna os ícones daquele monitor, sem apagar arquivos ou alterar suas posições.
A escolha fica salva mesmo após sair do app.
Ao parar ou sair do app, mostra a última imagem estática capturada por monitor.
A opção **Restaurar o fundo de antes** devolve o plugin e a imagem anteriores do Plasma.
Para o fundo estático, mantenha essa opção habilitada e aguarde a captura inicial.

A extensão KWin é carregada pelo app e descarregada ao sair. Ela informa quais
monitores estão cobertos por janelas em tela cheia ou maximizada, respeitando a
área de trabalho, atividade e janelas minimizadas. Não é necessário ativar a
extensão do GNOME. Ao migrar, conexões `HDMI-3` são reconhecidas como `HDMI-A-3`.

Para atualizar a integração, rode `./kde/install.sh` novamente e reabra o app.
Se o QML do plugin foi alterado, reinicie o Plasma com
`systemctl --user restart plasma-plasmashell.service` para limpar o código em cache.
A integração atual é para Plasma 6 em Wayland; não altera o fundo do SDDM.

## GNOME (Wayland)

O modo `--screen-root` do motor depende de `wlr-layer-shell`, que o GNOME não oferece. Por isso, no GNOME:

1. Ligue o **modo janela** nas configurações (o app roda o motor pelo XWayland, porque o GLEW não inicia no Wayland nativo).
2. Instale a extensão `extension/wpe-background@wpe-gui`, que move essa janela para a camada de fundo do GNOME:

```bash
./extension/install.sh   # depois, saia da sessão e entre de novo
```

Com ela, o wallpaper fica atrás dos apps e dos ícones da área de trabalho, cobre o monitor inteiro, não minimiza e não aparece na Visão geral.
Os cliques passam pela janela inteira do wallpaper, incluindo sua superfície interna,
para manter aplicativos e ícones clicáveis. Ao atualizar a extensão, execute novamente
`./extension/install.sh` e saia e entre na sessão para carregar o código novo.

### Testar a extensão sem relogar

`extension/dev/test-shell.sh` sobe um GNOME Shell sem tela, isolado da sua sessão, com a extensão, a DING e um app comum, e salva prints e o estado das camadas:

```bash
WPE_WALLPAPER=/caminho/workshop/content/431960/<id> WPE_ASSETS=/caminho/wallpaper_engine/assets \
  extension/dev/test-shell.sh
```

## Licença

MIT. Qualquer pessoa (inclusive os criadores do Wallpaper Engine) pode usar, modificar e redistribuir o código livremente. O motor linux-wallpaperengine é um programa separado, executado como processo externo, com a licença própria dele.

### Áudio por wallpaper

Cada wallpaper permite ajustar seu volume e escolher entre som ligado, silenciado ou o
padrão global do app. Wallpapers diferentes podem tocar em cada monitor; cópias do mesmo wallpaper compartilham uma única fonte de áudio. Os patches de SceneScript
e de espectro estão descritos em [Áudio dos wallpapers](docs/AUDIO.md).

A base do fork e os testes de compatibilidade estão em
[SceneScript](docs/SCENESCRIPT.md), com uma auditoria dos wallpapers instalados.

A barra inferior e o menu da bandeja também oferecem pausa global e por monitor,
independente das pausas automáticas do modo economia.
