# wpe-gui

Interface gráfica (Qt6/QML) para o [linux-wallpaperengine](https://github.com/Almamu/linux-wallpaperengine), com layout inspirado no Wallpaper Engine do Windows: grade de wallpapers, painel de preview à direita e página de configurações.

> Este projeto **não** inclui o motor nem os wallpapers. Você precisa do `linux-wallpaperengine` instalado e de uma cópia do Wallpaper Engine na Steam.

## Instalação

```bash
git clone https://github.com/Rk7gamerYT/wpe-gui.git && cd wpe-gui
./install.sh --dry-run   # mostra o que seria feito
./install.sh
```

O script cuida de Ubuntu/Debian, Fedora e Arch (e derivadas). Guia completo, passo a passo por distro, Steam, GNOME e problemas comuns: **[docs/INSTALL.md](docs/INSTALL.md)**.

## Status

Versão inicial (0.1). Já faz:

- Lista wallpapers instalados pela Steam (`steamapps/workshop/content/431960`) e pastas extras
- Busca e filtro por tipo
- Aplica/para o wallpaper (duplo clique ou botão), com **um wallpaper por monitor**, o mesmo **duplicado** em todos ou **esticado** entre eles
- Ajustes por wallpaper: escala, bordas e as propriedades do próprio wallpaper (sliders, cores, listas...)
- Restaura os wallpapers ao abrir o app
- **Modo economia:** pausa o wallpaper só no monitor que tiver um app em tela cheia ou maximizado (no GNOME, pela extensão)
- **Bandeja do sistema:** fechar a janela mantém o app e os wallpapers rodando; o ícone abre a interface de novo (há a opção "Iniciar escondido na bandeja") (no GNOME, usa a extensão AppIndicator, já ativa no Ubuntu)
- **Fundo estático:** ao fechar o app, o desktop fica com uma imagem do wallpaper em vez de voltar ao fundo antigo (GNOME)
- **Intensidade do áudio:** global e por wallpaper, para os que reagem ao som
- Configurações: FPS, volume, mudo, escala, pausa em tela cheia, modo janela

Planejado: playlists, iniciar com a sessão, Workshop.

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
