# wpe-gui

Interface gráfica (Qt6/QML) para o [linux-wallpaperengine](https://github.com/Almamu/linux-wallpaperengine), com layout inspirado no Wallpaper Engine do Windows: grade de wallpapers, painel de preview à direita e página de configurações.

> Este projeto **não** inclui o motor nem os wallpapers. Você precisa do `linux-wallpaperengine` instalado e de uma cópia do Wallpaper Engine na Steam.

## Status

Versão inicial (0.1). Já faz:

- Lista wallpapers instalados pela Steam (`steamapps/workshop/content/431960`) e pastas extras
- Busca e filtro por tipo
- Aplica/para o wallpaper (duplo clique ou botão)
- Configurações: FPS, volume, mudo, escala, pausa em tela cheia, modo janela

Planejado: propriedades por wallpaper (`--set-property`), playlists, multi-monitor, bandeja do sistema, iniciar com a sessão.

## Executar

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/wpe-gui
```

## Observação sobre GNOME/Wayland

O modo `--screen-root` do motor depende de `wlr-layer-shell`, que o GNOME não oferece. No GNOME use o **modo janela** nas configurações.

## Licença

MIT. Qualquer pessoa (inclusive os criadores do Wallpaper Engine) pode usar, modificar e redistribuir o código livremente. O motor linux-wallpaperengine é um programa separado, executado como processo externo, com a licença própria dele.
