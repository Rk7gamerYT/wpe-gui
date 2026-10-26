import QtQuick
import QtQuick.Window
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.plasmoid

WallpaperItem {
    id: root
    // Only the Folder View layer is hidden; widgets and the desktop stay active.
    // WallpaperItem is parented to the desktop's ContainmentItem by Plasma.
    readonly property Item iconLayer: parent && parent.isFolder === true ? parent.folderViewLayer : null

    contextualActions: [
        PlasmaCore.Action {
            text: "Mostrar ícones da área de trabalho"
            icon.name: "preferences-desktop-icons"
            checkable: true
            checked: root.configuration.ShowDesktopIcons
            enabled: root.iconLayer !== null
            onTriggered: {
                root.configuration.ShowDesktopIcons = checked;
                root.configuration.writeConfig();
            }
        }
    ]

    Binding {
        target: root.iconLayer
        property: "visible"
        value: root.configuration.ShowDesktopIcons
        when: root.iconLayer !== null
        restoreMode: Binding.RestoreBindingOrValue
    }

    // DesktopView clears its window to opaque black by default. Hiding the
    // wallpaper items alone does not make the icons' desktop surface transparent.
    Binding {
        target: root.Window.window
        property: "color"
        value: "transparent"
        when: root.configuration.Running && root.Window.window !== null
        restoreMode: Binding.RestoreBindingOrValue
    }
    // Transparent while the native Wayland surface draws underneath Plasma.
    Rectangle {
        anchors.fill: parent
        color: "#202124"
        visible: !root.configuration.Running
    }
    Image {
        anchors.fill: parent
        source: root.configuration.Image
        visible: !root.configuration.Running
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
    }
}
