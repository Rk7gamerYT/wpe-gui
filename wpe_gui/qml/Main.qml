import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: win
    width: 1280
    height: 760
    visible: true
    title: "Wallpaper Engine"
    color: "#1b1d23"

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
            x: 12
            font.pixelSize: 12
            opacity: 0.7
            text: backend.running ? "Em execução: " + backend.summary : "Nenhum wallpaper ativo"
        }
        Button {
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            height: 26
            text: "Parar"
            visible: backend.running
            onClicked: backend.stop()
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
