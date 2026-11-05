# Recuperar a versão antes da troca para Mint/Windows

A tag `backup-pre-mint-2026-11-04` preserva esta versão do aplicativo e os 14 patches
do motor. O motor original é fixado no commit
`b016d7d1fdcf4e5fd2f9c9fa420a8aaa07fee02d`; os patches são aplicados pelo instalador.
Não é necessário recuperar o binário compilado no CachyOS para recompilar no Mint.

## Recuperar o código

```sh
git clone --branch backup-pre-mint-2026-11-04 https://github.com/Rk7gamerYT/wpe-gui.git
cd wpe-gui
```

Para acompanhar versões novas, use um clone normal da `main` em vez da tag.
A tag abre a versão congelada em detached HEAD; crie uma branch antes de editar.

## Instalar no Linux

```sh
bash ./install.sh
```

Execute como usuário normal. O instalador solicita sudo para os pacotes,
compila o motor fixado com os patches e prepara o aplicativo.
A detecção das dependências inclui distribuições da família Ubuntu.
Isso não significa que a integração de desktop Cinnamon esteja validada:
as integrações específicas existentes são para GNOME e KDE Plasma.
A instalação do Mint requer validar separadamente a apresentação do wallpaper no Cinnamon.
Este projeto é a interface e o motor para Linux; não é um instalador do Wallpaper Engine para Windows.

## Recuperar os ajustes pessoais

O backup local feito antes da formatação contém `config/wpe-gui/settings.json` e
`config/wpe-gui/overrides.json`. Com o aplicativo fechado, copie esses arquivos para
`~/.config/wpe-gui/`. Os caminhos dos discos e os nomes das saídas podem mudar;
confira-os no aplicativo antes de reaplicar os wallpapers.

Os wallpapers do Workshop não estão no Git. Preserve separadamente a biblioteca
Steam e os assets do Wallpaper Engine, atualmente em outro disco.

## Verificar os patches

Após compilar, dentro do clone do aplicativo:

```sh
python3 scripts/check-engine-patches.py "$HOME/.local/share/wpe-gui/linux-wallpaperengine" --installed
```

O resultado esperado para esta versão é 14 patches aplicados e fontes correspondentes.
Há recursos de compatibilidade ainda incompletos; consulte `docs/SCENESCRIPT.md`.
