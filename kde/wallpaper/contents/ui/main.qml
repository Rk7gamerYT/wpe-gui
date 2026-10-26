import QtQuick
import QtQuick.Window
import org.kde.plasma.plasmoid

WallpaperItem {
    id: root
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
