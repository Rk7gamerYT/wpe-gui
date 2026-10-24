import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

// Controls generated from the wallpaper's project.json properties
ColumnLayout {
    id: root
    property string folder: ""
    property var items: []
    spacing: 10

    function reload() { items = folder ? properties.load(folder) : [] }
    // Bool/combo values can show or hide other properties (conditions), so they rebuild the list
    function commit(key, type, value) {
        properties.setValue(folder, key, value)
        if (type === "bool" || type === "combo") reload()
    }
    onFolderChanged: reload()

    RowLayout {
        Layout.fillWidth: true
        visible: root.items.length > 0
        Label { text: "Propriedades"; font.bold: true; Layout.fillWidth: true }
        Button {
            text: "Restaurar padrão"
            flat: true
            visible: root.items.some(i => i.modified)
            onClicked: { properties.reset(root.folder); root.reload() }
        }
    }

    Repeater {
        model: root.items
        delegate: Loader {
            id: row
            required property var modelData
            Layout.fillWidth: true
            sourceComponent: ({
                bool: boolControl, slider: sliderControl, color: colorControl,
                combo: comboControl, textinput: textControl, text: labelControl, group: groupControl
            })[modelData.type]
        }
    }

    Component {
        id: boolControl
        Switch {
            width: parent.width
            text: modelData.label
            checked: modelData.value
            onToggled: root.commit(modelData.key, "bool", checked)
        }
    }

    Component {
        id: sliderControl
        ColumnLayout {
            width: parent.width
            spacing: 0
            RowLayout {
                Label { text: modelData.label; Layout.fillWidth: true; elide: Text.ElideRight }
                Label { id: shown; opacity: 0.7; text: slider.value.toFixed(modelData.step < 1 ? 2 : 0) }
            }
            Slider {
                id: slider
                Layout.fillWidth: true
                from: modelData.min; to: modelData.max; stepSize: modelData.step
                value: modelData.value
                onMoved: if (!pressed) root.commit(modelData.key, "slider", value)
                onPressedChanged: if (!pressed) root.commit(modelData.key, "slider", value)
            }
        }
    }

    Component {
        id: colorControl
        RowLayout {
            width: parent.width
            function parts() { return String(modelData.value).split(/\s+/).map(Number) }
            Label { text: modelData.label; Layout.fillWidth: true; elide: Text.ElideRight }
            Rectangle {
                width: 44; height: 22; radius: 3
                border.color: "#555"
                color: { const p = parts(); return Qt.rgba(p[0], p[1], p[2], 1) }
                MouseArea { anchors.fill: parent; onClicked: dialog.open() }
            }
            ColorDialog {
                id: dialog
                selectedColor: { const p = parts(); return Qt.rgba(p[0], p[1], p[2], 1) }
                onAccepted: root.commit(modelData.key, "color",
                    [selectedColor.r, selectedColor.g, selectedColor.b].map(v => v.toFixed(5)).join(" "))
            }
        }
    }

    Component {
        id: comboControl
        ColumnLayout {
            width: parent.width
            spacing: 2
            Label { text: modelData.label; elide: Text.ElideRight; Layout.fillWidth: true }
            ComboBox {
                Layout.fillWidth: true
                model: modelData.options
                textRole: "label"
                currentIndex: Math.max(0, modelData.options.findIndex(o => o.value === String(modelData.value)))
                onActivated: root.commit(modelData.key, "combo", modelData.options[currentIndex].value)
            }
        }
    }

    Component {
        id: textControl
        ColumnLayout {
            width: parent.width
            spacing: 2
            Label { text: modelData.label; elide: Text.ElideRight; Layout.fillWidth: true }
            TextField {
                Layout.fillWidth: true
                text: modelData.value
                onEditingFinished: root.commit(modelData.key, "textinput", text)
            }
        }
    }

    Component {
        id: labelControl
        Label { width: parent.width; text: modelData.label; wrapMode: Text.Wrap; opacity: 0.75; font.pixelSize: 12 }
    }

    Component {
        id: groupControl
        Label { width: parent.width; text: modelData.label; font.bold: true; topPadding: 6 }
    }
}
