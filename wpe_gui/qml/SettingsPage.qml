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

        Label { text: "Silenciar" }
        Switch { checked: settings.value("silent"); onToggled: settings.set("silent", checked) }

        Label { text: "Silenciar quando outro app tocar áudio" }
        Switch { checked: settings.value("autoMute"); onToggled: settings.set("autoMute", checked) }

        Label { text: "Pausar com app em tela cheia" }
        Switch { checked: settings.value("pauseOnFullscreen"); onToggled: settings.set("pauseOnFullscreen", checked) }

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

        Label { text: "Monitor (modo root)" }
        TextField {
            Layout.fillWidth: true
            text: settings.value("screen")
            onEditingFinished: settings.set("screen", text)
        }
    }
}
