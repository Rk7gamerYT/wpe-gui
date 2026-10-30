## Um único arquivo para usar

Baixe **wpe-gui-0.2.0-x86_64.AppImage**, permita sua execução e abra o arquivo.
O pacote inclui Python, Qt, motor corrigido, CEF e bibliotecas de mídia. Não é
necessário instalar Python, compilar o motor ou baixar plugins separadamente.
As integrações KDE/GNOME acompanham o pacote e são registradas no seu usuário.

Requisitos: desktop Linux x86_64 com glibc 2.39 ou mais recente e drivers gráficos
funcionando. A base de construção é Ubuntu 24.04; o alvo são Ubuntu 24.04/26.04,
Debian 13, Fedora atual, Arch/derivadas e openSUSE Leap 16/Tumbleweed. Outras versões
não são prometidas como compatíveis sem teste.

**O Wallpaper Engine e seus assets precisam estar instalados pelo Steam.** Esses
arquivos comerciais não são redistribuídos no pacote.

## Atualizador integrado

Em **Configurações → Atualizações**, use **Verificar**, **Atualizar agora** e
**Reiniciar app**. A atualização baixa o AppImage completo e verifica seu SHA-256
antes de substituir o arquivo atual. Falhas de download/verificação preservam a
versão anterior. Nenhuma atualização é instalada sem o clique do usuário.

## Correções e novidades

- Áudio em todos os monitores para wallpapers diferentes, sem duplicar o som de cópias do mesmo wallpaper.
- Volume e silenciamento por wallpaper; intensidade do espectro atualizada nos processos em execução.
- Pausa manual global e por monitor, também na bandeja, sem perder as pausas do modo economia.
- Buffers de áudio para SceneScript, frequências mapeadas e correção do ângulo das barras do espectro.
- Correções em módulos, grupos, texto, vetores, temporizadores e tratamento de metadados inválidos.

A cobertura e as lacunas de SceneScript continuam documentadas em `docs/SCENESCRIPT.md`.
Os arquivos de código-fonte e patches são opcionais para desenvolvimento; não são
necessários para executar o AppImage.
