import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    height: 52
    color: "#15171c"

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 12
        anchors.rightMargin: 12
        spacing: 8

        Repeater {
            model: [
                { id: "installed", label: "Instalados" },
                { id: "settings", label: "Configurações" }
            ]
            delegate: TabButton {
                required property var modelData
                text: modelData.label
                checked: win.page === modelData.id
                onClicked: win.page = modelData.id
                width: implicitWidth
            }
        }

        Item { Layout.fillWidth: true }

        ComboBox {
            visible: win.page === "installed"
            model: ["Todos", "Scene", "Video", "Web"]
            onActivated: wallpapers.typeFilter = currentIndex === 0 ? "" : currentText
        }

        TextField {
            visible: win.page === "installed"
            Layout.preferredWidth: 240
            placeholderText: "Pesquisar..."
            onTextChanged: wallpapers.query = text
        }

        Button {
            visible: win.page === "installed"
            text: "Recarregar"
            onClicked: library.reload()
        }
    }
}
