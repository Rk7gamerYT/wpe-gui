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

        // Description, tags and the wallpaper's own properties scroll together
        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: availableWidth
            clip: true

            ColumnLayout {
                width: parent.width
                spacing: 12

                Label {
                    Layout.fillWidth: true
                    text: win.selected ? win.selected.description : ""
                    visible: text !== ""
                    wrapMode: Text.Wrap
                    opacity: 0.8
                    maximumLineCount: 6
                    elide: Text.ElideRight
                }
                Label {
                    Layout.fillWidth: true
                    text: win.selected && win.selected.tags ? "Tags: " + win.selected.tags : ""
                    visible: text !== ""
                    wrapMode: Text.Wrap
                    opacity: 0.6
                    font.pixelSize: 11
                }
                PropertiesList {
                    Layout.fillWidth: true
                    folder: win.selected ? win.selected.path : ""
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 0

            Button {
                Layout.fillWidth: true
                text: win.layout === "independent" && backend.screenNames().length > 1
                      ? "Aplicar em todos os monitores" : "Aplicar wallpaper"
                highlighted: true
                onClicked: backend.applyTo(win.selected.path, "")
            }
            // Only the "one wallpaper per monitor" layout lets you pick a monitor
            Button {
                visible: win.layout === "independent" && backend.screenNames().length > 1
                text: "▾"
                highlighted: true
                onClicked: monitorMenu.popup()
                Menu {
                    id: monitorMenu
                    Repeater {
                        model: backend.screenNames()
                        MenuItem {
                            required property string modelData
                            text: "Aplicar só em " + modelData
                            onTriggered: backend.applyTo(win.selected.path, modelData)
                        }
                    }
                    MenuSeparator {}
                    MenuItem { text: "Parar este wallpaper"; onTriggered: backend.stopPath(win.selected.path) }
                }
            }
        }
    }

    Label {
        anchors.centerIn: parent
        visible: win.selected === null
        opacity: 0.5
        text: "Selecione um wallpaper"
    }
}
