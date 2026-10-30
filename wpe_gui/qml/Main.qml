import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQml.Models

ApplicationWindow {
    id: win
    width: 1280
    height: 760
    visible: true
    title: "Wallpaper Engine"
    color: "#1b1d23"
    onClosing: function(close) {
        if (loginBackground.busy) {
            close.accepted = false
            toast.show("Conclua ou cancele a autenticação da tela de login antes de fechar.")
        }
    }

    property var selected: null
    property string page: "installed"
    property string layout: settings.value("layout")
    Connections {
        target: settings
        function onChanged() { win.layout = settings.value("layout") }
    }

    palette.window: "#1b1d23"
    palette.windowText: "#e6e8ee"
    palette.base: "#23262e"
    palette.text: "#e6e8ee"
    palette.button: "#2c303a"
    palette.buttonText: "#e6e8ee"
    palette.highlight: "#3d8bff"

    Connections {
        target: backend
        function onMessage(text) { toast.show(text) }
    }

    header: TopBar {}

    RowLayout {
        anchors.fill: parent
        spacing: 0

        // Main area
        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: win.page === "installed" ? 0 : 1

            WallpaperGrid {}
            SettingsPage {}
        }

        // Right-hand preview/properties panel, as in the Windows app
        PreviewPanel {
            Layout.preferredWidth: 320
            Layout.fillHeight: true
            visible: win.page === "installed"
        }
    }

    footer: Rectangle {
        height: 32
        color: "#15171c"
        Label {
            anchors.verticalCenter: parent.verticalCenter
            anchors.left: parent.left
            anchors.leftMargin: 12
            anchors.right: playbackButtons.left
            anchors.rightMargin: 12
            elide: Text.ElideRight
            font.pixelSize: 12
            opacity: 0.7
            text: backend.running ? "Em execução: " + backend.summary : "Nenhum wallpaper ativo"
        }
        Row {
            id: playbackButtons
            anchors.right: parent.right
            anchors.rightMargin: 8
            anchors.verticalCenter: parent.verticalCenter
            spacing: 6
            Button {
                height: 26
                text: backend.hasManualPause ? "Retomar todos" : "Pausar todos"
                enabled: backend.running
                onClicked: backend.setGlobalPaused(!backend.hasManualPause)
            }
            Button {
                height: 26
                text: "Monitores"
                enabled: backend.running
                onClicked: monitorPauseMenu.popup()
                Menu {
                    id: monitorPauseMenu
                    Instantiator {
                        model: backend.playbackTargets
                        delegate: MenuItem {
                            required property var modelData
                            text: modelData.label + (modelData.paused && !modelData.manuallyPaused ? " (pausa automática)" : "")
                            checkable: true
                            checked: modelData.manuallyPaused
                            onTriggered: backend.setTargetPaused(modelData.key, !modelData.manuallyPaused)
                        }
                        onObjectAdded: function(index, object) { monitorPauseMenu.insertItem(index, object) }
                        onObjectRemoved: function(index, object) { monitorPauseMenu.removeItem(object) }
                    }
                }
            }
            Button {
                height: 26
                text: "Restaurar wallpapers"
                enabled: backend.canRestore
                onClicked: backend.restore()
            }
            Button {
                height: 26
                text: "Parar"
                enabled: backend.running
                onClicked: backend.stop()
            }
        }
    }

    Rectangle {
        id: toast
        property alias text: toastLabel.text
        function show(t) { text = t; opacity = 1; hide.restart() }
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 56
        width: toastLabel.implicitWidth + 32
        height: 40
        radius: 6
        color: "#3a2f33"
        opacity: 0
        Behavior on opacity { NumberAnimation { duration: 150 } }
        Label { id: toastLabel; anchors.centerIn: parent }
        Timer { id: hide; interval: 4000; onTriggered: toast.opacity = 0 }
    }
}
