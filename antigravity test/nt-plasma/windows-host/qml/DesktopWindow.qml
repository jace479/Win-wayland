import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Window {
    id: desktopWindow
    visible: true
    title: "KWin-Win Desktop"
    flags: Qt.FramelessWindowHint | Qt.WindowDoesNotAcceptFocus

    property int winX: 0
    property int winY: 0
    property int winW: (typeof screenWidth !== "undefined" && screenWidth > 0) ? screenWidth : Screen.width
    property int winH: (typeof screenHeight !== "undefined" && screenHeight > 0) ? screenHeight : Screen.height
    property bool isPrimary: true

    x: winX
    y: winY
    width: winW
    height: winH
    color: "#0a0e17"

    // KDE Plasma 6 Breeze Wallpaper (Rich Dark Gradient + Geometric Accents)
    Rectangle {
        anchors.fill: parent

        gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop { position: 0.0; color: "#0a0e17" }
            GradientStop { position: 0.25; color: "#121b28" }
            GradientStop { position: 0.6; color: "#182638" }
            GradientStop { position: 0.85; color: "#1e3149" }
            GradientStop { position: 1.0; color: "#141f2d" }
        }

        // KDE Geometric Polyhedra Accent 1 (Cyan / Breeze Blue)
        Rectangle {
            x: parent.width * 0.55
            y: parent.height * 0.15
            width: 520
            height: 520
            radius: 260
            rotation: 35
            color: "transparent"
            border.color: "#1a3daee9"
            border.width: 120

            Rectangle {
                anchors.centerIn: parent
                width: 320
                height: 320
                radius: 160
                color: "transparent"
                border.color: "#0f23d18b"
                border.width: 60
            }
        }

        // KDE Geometric Polyhedra Accent 2 (Magenta / Violet Glow)
        Rectangle {
            x: parent.width * 0.2
            y: parent.height * 0.45
            width: 440
            height: 440
            radius: 220
            rotation: -25
            color: "transparent"
            border.color: "#129b59b6"
            border.width: 90
        }

        // Plasma Desktop Clock & Date Widget (Top Right)
        ColumnLayout {
            visible: desktopWindow.isPrimary
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: 48
            spacing: 2

            Text {
                id: bigClockTime
                Layout.alignment: Qt.AlignRight
                text: Qt.formatDateTime(new Date(), "h:mm ap")
                font.pixelSize: 68
                font.weight: Font.Light
                color: "#f0eff0f1"
            }

            Text {
                id: bigClockDate
                Layout.alignment: Qt.AlignRight
                text: Qt.formatDateTime(new Date(), "dddd, MMMM d, yyyy")
                font.pixelSize: 18
                font.weight: Font.Normal
                color: "#a63daee9"
            }

            Text {
                Layout.alignment: Qt.AlignRight
                Layout.topMargin: 6
                text: "KDE Plasma 6 • Windows 10/11 Shell"
                font.pixelSize: 12
                font.weight: Font.DemiBold
                color: "#77eff0f1"
            }

            Timer {
                interval: 1000
                running: true
                repeat: true
                onTriggered: {
                    var now = new Date();
                    bigClockTime.text = Qt.formatDateTime(now, "h:mm ap");
                    bigClockDate.text = Qt.formatDateTime(now, "dddd, MMMM d, yyyy");
                }
            }
        }

        // Desktop Right-Click Context Menu
        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.RightButton
            onClicked: desktopMenu.popup()
        }

        Menu {
            id: desktopMenu
            MenuItem {
                text: "⚙ Open Application Menu"
                onTriggered: trayBridge.sendTrayClick(0, 1001, 1)
            }
            MenuItem {
                text: "💻 Open Terminal (Konsole)"
                onTriggered: trayBridge.sendTrayClick(0, 1003, 1)
            }
            MenuItem {
                text: "📁 Open File Manager (Dolphin)"
                onTriggered: trayBridge.sendTrayClick(0, 1002, 1)
            }
            MenuSeparator {}
            MenuItem {
                text: "🔄 Refresh Application Catalog"
                onTriggered: appModel.reloadApplications()
            }
        }
    }
}
