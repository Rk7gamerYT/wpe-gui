# Patches do motor

Aplicar, na ordem dos nomes, ao commit `b016d7d1fdcf4e5fd2f9c9fa420a8aaa07fee02d`
de [Almamu/linux-wallpaperengine](https://github.com/Almamu/linux-wallpaperengine).

Os patches são modificações do motor e seguem sua licença GNU GPL versão 3,
cuja cópia está em `COPYING.engine`. A licença MIT da interface não substitui
as licenças do motor nem das bibliotecas distribuídas com ele.

O AppImage contém o motor já corrigido. Quem usa o pacote completo não precisa
aplicar patches ou compilar. O código correspondente e os scripts de construção
estão disponíveis na mesma release.

Para verificar a série sem alterar um checkout do motor:

```sh
python3 scripts/check-engine-patches.py /caminho/do/linux-wallpaperengine
```
