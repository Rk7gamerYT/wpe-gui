import QtQuick
import QtQuick.Controls

Item {
    GridView {
        id: grid
        anchors.fill: parent
        anchors.margins: 12
        cellWidth: 190
        cellHeight: 190
        clip: true
        model: wallpapers
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar {}

        delegate: Item {
            id: cell
            required property string title
            required property string preview
            required property string path
            required property string wtype
            required property string description
            required property string tags
            required property int index
            width: grid.cellWidth
            height: grid.cellHeight

            Rectangle {
                anchors.fill: parent
                anchors.margins: 6
                radius: 4
                color: "#23262e"
                border.width: win.selected && win.selected.path === cell.path ? 2 : 0
                border.color: "#3d8bff"

                Image {
                    anchors.fill: parent
                    anchors.bottomMargin: 28
                    source: cell.preview
                    fillMode: Image.PreserveAspectCrop
                    asynchronous: true
                    sourceSize.width: 360
                }
                Label {
                    anchors.bottom: parent.bottom
                    anchors.left: parent.left
                    anchors.right: parent.right
                    height: 28
                    leftPadding: 8
                    rightPadding: 8
                    verticalAlignment: Text.AlignVCenter
                    elide: Text.ElideRight
                    text: cell.title
                    font.pixelSize: 12
                }
                Rectangle {
                    visible: backend.active.indexOf(cell.path) >= 0
                    anchors.top: parent.top
                    anchors.right: parent.right
                    anchors.margins: 6
                    width: 10; height: 10; radius: 5
                    color: "#4cd964"
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: win.selected = { title: cell.title, preview: cell.preview, path: cell.path,
                                                wtype: cell.wtype, description: cell.description, tags: cell.tags }
                    onDoubleClicked: { clicked(null); backend.apply(cell.path) }
                }
            }
        }

        Label {
            anchors.centerIn: parent
            visible: grid.count === 0
            horizontalAlignment: Text.AlignHCenter
            opacity: 0.6
            text: "Nenhum wallpaper encontrado.\nAdicione uma pasta em Configurações\nou instale wallpapers pelo Steam."
        }
    }
}
