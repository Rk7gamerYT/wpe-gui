# KDE Plasma no Ubuntu 26.04

Guia para usar o **wpe-gui** no Ubuntu 26.04 LTS com **KDE Plasma 6 em Wayland**.
A integração foi verificada no Ubuntu 26.04.1 com dois monitores, incluindo um na vertical.

O projeto fornece a interface, o plugin de wallpaper do Plasma e a extensão KWin.
Os wallpapers e os assets continuam dependendo de uma cópia do **Wallpaper Engine na Steam**.

## 1. Entrar no KDE Plasma

Se já usa Kubuntu ou está numa sessão Plasma, avance para a etapa 2.
Se usa Ubuntu com GNOME, pode instalar o KDE sem formatar. Faça backup dos arquivos
importantes antes de alterar o ambiente gráfico.

```bash
sudo apt update
sudo apt install kubuntu-desktop
```

Se aparecer a escolha do gerenciador de login, selecione **sddm**.
Salve seu trabalho e reinicie o computador. Na tela de login, escolha a sessão
**Plasma (Wayland)**, quando houver uma escolha de sessões.
Mantenha o GNOME instalado durante o teste; não é necessário removê-lo para usar o app.

Confira no Konsole:

```bash
printf 'Desktop: %s\nTipo da sessão: %s\n' "$XDG_CURRENT_DESKTOP" "$XDG_SESSION_TYPE"
```

O desktop deve conter `KDE` e o tipo da sessão deve ser `wayland`.
Este guia não cobre Plasma em X11.

## 2. Instalar o Wallpaper Engine pela Steam

1. Tenha o Wallpaper Engine na sua conta Steam.
2. Na Steam, habilite a compatibilidade Steam Play/Proton para permitir instalar o programa.
3. Instale o Wallpaper Engine. O wpe-gui utiliza os arquivos dele; não exige manter o programa Windows aberto.
4. Inscreva-se nos wallpapers desejados na Oficina da Steam e espere os downloads terminarem.

Os assets ficam em `steamapps/common/wallpaper_engine/assets` e os wallpapers,
em `steamapps/workshop/content/431960`. O app procura as bibliotecas Steam automaticamente.
Se a biblioteca estiver em outro disco, monte esse disco antes de abrir o app.

## 3. Baixar e instalar o projeto

Execute os comandos como seu usuário normal; não rode o instalador inteiro com `sudo`.
Ele solicita autenticação apenas para instalar os pacotes do sistema.

```bash
curl -fsSL https://raw.githubusercontent.com/Rk7gamerYT/wpe-gui/main/install-online.sh | bash
```

Não é necessário clonar o projeto, instalar o motor à parte ou preencher seu caminho.
Quando terminar, abra **Wallpaper Engine** pelo menu de aplicativos.
O app fica em `~/.local/share/wpe-gui/app` e o log em
`~/.local/state/wpe-gui/install.log`.

O instalador:

- instala as dependências do Ubuntu;
- compila a versão fixada do `linux-wallpaperengine` com os patches do projeto;
- prepara o ambiente Python e instala a entrada no menu de aplicativos;
- detecta a sessão KDE e instala o plugin Plasma e a extensão KWin no seu usuário.

A compilação pode levar alguns minutos. O número de tarefas paralelas é limitado
pela memória disponível. Não substitua esse limite por `make -j$(nproc)` sem avaliar o consumo de RAM.

Se o app e o motor com os patches já estão instalados, atualize somente a integração:

```bash
cd /caminho/para/wpe-gui
git pull --ff-only
./kde/install.sh
```

Os novos arquivos ficam em:

```text
~/.local/share/plasma/wallpapers/org.wpegui.wallpaper/
~/.local/share/kwin/scripts/wpe-gui/
```

## 4. Aplicar um wallpaper

Abra **Wallpaper Engine** pelo menu de aplicativos. Para executar pelo terminal:

```bash
~/.local/bin/wpe-gui
```

Se instalou manualmente a partir de um clone Git, também pode usar `./wpe-gui.sh` dentro dele.

1. Escolha um wallpaper na biblioteca e clique em **Aplicar**.
2. Com vários monitores, use a seta ao lado do botão para escolher o destino.
3. Ajuste FPS, volume, escala e propriedades conforme necessário.
4. Em **Configurações**, escolha a pausa automática: desligada, tela cheia ou janela maximizada.
5. Para iniciar junto com a sessão, ative **Iniciar com o sistema** e **Restaurar wallpapers ao abrir o app**.
   Ative **Iniciar escondido na bandeja** se preferir não abrir a janela no login.

No KDE/Wayland, o modo nativo é selecionado automaticamente. A configuração de modo
janela de uma sessão GNOME anterior não força o uso de XWayland.
O plugin **Wallpaper Engine (wpe-gui)** é aplicado pelo app: não é preciso escolhê-lo manualmente.
A extensão GNOME não é utilizada nesta sessão.

O plugin mantém transparentes o fundo e a janela do desktop, para a animação aparecer
atrás dos ícones e widgets. A extensão KWin pausa apenas os monitores cobertos por
janelas em tela cheia ou maximizada. Janelas minimizadas ou em outra atividade/área
de trabalho não contam. No modo esticado, a animação pausa quando todos os monitores estão cobertos.

Fechar a janela mantém o app na bandeja, conforme a configuração. Para encerrar de fato,
use **Sair** no menu da bandeja. Com **Fundo estático ao fechar o app** habilitado,
aguarde a captura inicial: ao parar o motor, a última imagem capturada fica no desktop.
O fundo estático não é uma captura contínua do último quadro da animação.

## Verificar a integração

Com o app aberto, no Konsole:

```bash
qdbus6 org.kde.KWin /Scripting org.kde.kwin.Scripting.isScriptLoaded wpe-gui
qdbus6 org.wpegui.KWin /org/wpegui/KWin org.wpegui.KWin.GetCovered
```

O primeiro comando deve retornar `true`. O segundo mostra os retângulos dos monitores
cobertos por janelas em tela cheia ou maximizada; listas vazias são normais quando
nenhuma janela cobre um monitor. Maximize uma janela e depois minimize-a para verificar a mudança.

A extensão KWin é carregada enquanto o app está aberto e descarregada ao sair.
Não é preciso habilitá-la permanentemente nas configurações do KWin.

## Atualizar

Encerre o app pelo menu da bandeja antes de atualizar. Se instalou pelo comando único,
execute-o novamente:

```bash
curl -fsSL https://raw.githubusercontent.com/Rk7gamerYT/wpe-gui/main/install-online.sh | bash
```

Se aparecer a orientação para recarregar o Plasma, execute
`systemctl --user restart plasma-plasmashell.service` e reabra o app.

Para um clone Git, use:

```bash
cd /caminho/para/wpe-gui
git pull --ff-only
./kde/install.sh
systemctl --user restart plasma-plasmashell.service
./wpe-gui.sh
```

O reinício do Plasma faz a barra e o desktop desaparecerem brevemente, sem encerrar
os outros aplicativos. Ele é necessário quando o QML do plugin mudou, porque o Plasma
pode manter o código antigo em cache. Sair da sessão e entrar novamente também recarrega o plugin.

Para atualizar também o motor e seus patches, use `./install.sh --no-deps` no lugar
de `./kde/install.sh`, se as dependências do sistema já estiverem instaladas.

## Solução de problemas

### O wallpaper desaparece onde há ícones ou o desktop fica preto

Atualize o projeto, rode `./kde/install.sh` e reinicie o Plasma como na seção anterior.
A integração precisa tornar transparente também a janela que contém os ícones,
que por padrão é preenchida de preto pelo Plasma.
Não é necessário apagar os ícones nem redefinir as configurações do KDE.

Se só um wallpaper específico continua preto, confira os patches do motor e teste
outro wallpaper; erros de shader são um problema diferente da camada do desktop.

### A pausa automática não funciona

Confira se **Modo economia** está habilitado e execute os comandos da seção
[Verificar a integração](#verificar-a-integração). Se a extensão não estiver carregada,
rode `./kde/install.sh` e encerre/reabra o app. O log do motor fica em
`~/.local/state/wpe-gui/engine.log`.

### O monitor HDMI perdeu o wallpaper após sair do GNOME

O app reconhece automaticamente a mudança de nome de `HDMI-3` para `HDMI-A-3`.
Se o conector mudou de outra forma, aplique novamente o wallpaper no monitor correto.

### Erros de qt6ct ou Kvantum depois de migrar do GNOME

Uma configuração antiga pode estar forçando um tema que não está disponível no Qt do app.
Para testar o app sem essas variáveis, execute:

```bash
env -u QT_QPA_PLATFORMTHEME -u QT_STYLE_OVERRIDE ./wpe-gui.sh
```

Se isso resolver, revise as definições dessas variáveis em `~/.config/environment.d/`
e `/etc/environment.d/`, preservando uma cópia antes de editar. Não é preciso apagar toda a configuração do KDE.

### Quero voltar ao fundo anterior

Use **Configurações → Restaurar o fundo de antes** no app antes de desinstalar a integração.
Depois encerre o app pela bandeja. Para remover os plugins instalados neste usuário:

```bash
rm -rf ~/.local/share/plasma/wallpapers/org.wpegui.wallpaper
rm -rf ~/.local/share/kwin/scripts/wpe-gui
```

Se usa `XDG_DATA_HOME` personalizado, substitua `~/.local/share` pelo caminho configurado.
A integração não modifica o fundo de login do **SDDM**. O recurso de fundo de login
Ubuntu/GDM descrito no README é separado.

## Referências técnicas

- [API de scripts do KWin](https://develop.kde.org/docs/plasma/kwin/api/)
- [API de scripts do Plasma](https://develop.kde.org/docs/plasma/scripting/api/)
- [Motor linux-wallpaperengine](https://github.com/Almamu/linux-wallpaperengine)
