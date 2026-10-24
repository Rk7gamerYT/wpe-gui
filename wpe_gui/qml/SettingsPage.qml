import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

ScrollView {
    contentWidth: availableWidth

    GridLayout {
        x: 24; y: 24
        width: Math.min(parent.width - 48, 640)
        columns: 2
        columnSpacing: 16
        rowSpacing: 14

        Label { text: "Caminho do linux-wallpaperengine" }
        TextField {
            Layout.fillWidth: true
            placeholderText: "(usar o do PATH)"
            text: settings.value("enginePath")
            onEditingFinished: settings.set("enginePath", text)
        }

        Label { text: "Steam detectada" }
        Label {
            Layout.fillWidth: true
            wrapMode: Text.WrapAnywhere
            opacity: 0.7
            text: library.detectedDirs().length ? library.detectedDirs().join("\n")
                                                : "Nenhuma pasta de workshop encontrada automaticamente"
        }

        Label { text: "Pastas manuais de wallpapers" }
        RowLayout {
            Layout.fillWidth: true
            TextField {
                id: dirsField
                Layout.fillWidth: true
                placeholderText: "/caminho/1, /caminho/2"
                text: settings.value("libraryDirs").join(", ")
                onEditingFinished: {
                    settings.set("libraryDirs", text.split(",").map(s => s.trim()).filter(s => s))
                    library.reload()
                }
            }
            Button { text: "Adicionar..."; onClicked: dirDialog.open() }
        }

        Label { text: "Pasta assets do Wallpaper Engine" }
        RowLayout {
            Layout.fillWidth: true
            TextField {
                Layout.fillWidth: true
                placeholderText: library.detectedAssets() || "(não detectada)"
                text: settings.value("assetsDir")
                onEditingFinished: settings.set("assetsDir", text)
            }
            Button { text: "Escolher..."; onClicked: assetsDialog.open() }
        }

        FolderDialog {
            id: dirDialog
            title: "Pasta com wallpapers"
            onAccepted: {
                const p = selectedFolder.toString().replace("file://", "")
                const list = settings.value("libraryDirs")
                if (list.indexOf(p) < 0) list.push(p)
                settings.set("libraryDirs", list)
                dirsField.text = list.join(", ")
                library.reload()
            }
        }
        FolderDialog {
            id: assetsDialog
            title: "Pasta assets (steamapps/common/wallpaper_engine/assets)"
            onAccepted: settings.set("assetsDir", selectedFolder.toString().replace("file://", ""))
        }

        Label { text: "FPS" }
        SpinBox {
            from: 5; to: 144
            value: settings.value("fps")
            onValueModified: settings.set("fps", value)
        }

        Label { text: "Volume" }
        Slider {
            Layout.fillWidth: true
            from: 0; to: 100; stepSize: 1
            value: settings.value("volume")
            onMoved: settings.set("volume", Math.round(value))
        }

        Label { text: "Intensidade do áudio (padrão)" }
        RowLayout {
            Layout.fillWidth: true
            Slider {
                id: gainDefault
                Layout.fillWidth: true
                from: 0; to: 300; stepSize: 5
                value: 100 * settings.value("audioGain")
                onPressedChanged: if (!pressed) settings.set("audioGain", value / 100)
            }
            Label { text: Math.round(gainDefault.value) + "%"; Layout.preferredWidth: 38; horizontalAlignment: Text.AlignRight }
        }
        Label {
            Layout.columnSpan: 2
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            opacity: 0.6
            font.pixelSize: 11
            text: "Vale para wallpapers que reagem ao som. Cada wallpaper pode ter a sua, no painel da direita."
        }

        Label { text: "Silenciar" }
        Switch { checked: settings.value("silent"); onToggled: settings.set("silent", checked) }

        Label { text: "Silenciar quando outro app tocar áudio" }
        Switch { checked: settings.value("autoMute"); onToggled: settings.set("autoMute", checked) }

        Label { text: "Modo economia" }
        ComboBox {
            Layout.fillWidth: true
            readonly property var values: ["off", "fullscreen", "maximized"]
            model: ["Desligado", "Pausar com app em tela cheia", "Pausar com app maximizado ou em tela cheia"]
            currentIndex: Math.max(0, values.indexOf(settings.value("powerSaving")))
            onActivated: settings.set("powerSaving", values[currentIndex])
        }
        Label {
            Layout.columnSpan: 2
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            opacity: 0.6
            font.pixelSize: 11
            text: "O wallpaper é pausado só no monitor que tiver o app. No GNOME isso depende da extensão instalada."
        }

        Label { text: "Desativar interação do mouse" }
        Switch { checked: settings.value("disableMouse"); onToggled: settings.set("disableMouse", checked) }

        Label { text: "Escala" }
        ComboBox {
            model: ["default", "stretch", "fit", "fill"]
            currentIndex: model.indexOf(settings.value("scaling"))
            onActivated: settings.set("scaling", currentText)
        }

        Label { text: "Modo janela (para GNOME/Wayland sem layer-shell)" }
        Switch { checked: settings.value("windowed"); onToggled: settings.set("windowed", checked) }

        Label { text: "Vários monitores" }
        ComboBox {
            readonly property var values: ["independent", "duplicate", "span"]
            model: ["Um wallpaper por monitor", "Duplicar em todos", "Esticar entre os monitores"]
            currentIndex: Math.max(0, values.indexOf(settings.value("layout")))
            onActivated: settings.set("layout", values[currentIndex])
        }

        Label { text: "Restaurar wallpapers ao abrir o app" }
        Switch { checked: settings.value("restoreOnStart"); onToggled: settings.set("restoreOnStart", checked) }

        Label { text: "Fundo estático ao fechar o app"; visible: staticBackground.supported }
        Switch {
            visible: staticBackground.supported
            checked: settings.value("staticBackground")
            onToggled: settings.set("staticBackground", checked)
        }
        Label {
            visible: staticBackground.supported
            Layout.columnSpan: 2
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            opacity: 0.6
            font.pixelSize: 11
            text: "Mantém uma imagem do wallpaper como fundo do sistema, então ao fechar o app o desktop não volta ao fundo antigo."
        }
        Label { text: "Fundo original do sistema"; visible: staticBackground.supported }
        Button {
            visible: staticBackground.supported
            text: "Restaurar o fundo de antes"
            onClicked: staticBackground.restoreOriginal()
        }

    }
}
