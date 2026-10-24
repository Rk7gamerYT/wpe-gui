import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    color: "#15171c"

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 10
        visible: win.selected !== null

        Image {
            Layout.fillWidth: true
            Layout.preferredHeight: width * 9 / 16
            source: win.selected ? win.selected.preview : ""
            fillMode: Image.PreserveAspectCrop
            asynchronous: true
        }
        Label {
            Layout.fillWidth: true
            text: win.selected ? win.selected.title : ""
            font.pixelSize: 18
            font.bold: true
            wrapMode: Text.Wrap
        }
        Label {
            text: win.selected ? win.selected.wtype.toUpperCase() : ""
            opacity: 0.6
            font.pixelSize: 11
        }
        Label {
            Layout.fillWidth: true
            text: win.selected ? win.selected.description : ""
            wrapMode: Text.Wrap
            opacity: 0.8
            elide: Text.ElideRight
            maximumLineCount: 6
        }
        Label {
            Layout.fillWidth: true
            text: win.selected && win.selected.tags ? "Tags: " + win.selected.tags : ""
            wrapMode: Text.Wrap
            opacity: 0.6
            font.pixelSize: 11
        }

        Item { Layout.fillHeight: true }

        Button {
            Layout.fillWidth: true
            text: "Aplicar wallpaper"
            highlighted: true
            onClicked: backend.apply(win.selected.path)
        }
    }

    Label {
        anchors.centerIn: parent
        visible: win.selected === null
        opacity: 0.5
        text: "Selecione um wallpaper"
    }
}
