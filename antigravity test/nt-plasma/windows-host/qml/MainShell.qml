import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: shellRoot

    // ========================================================================
    // 1. Full-Screen KDE Plasma 6 Desktop Canvas Window (HWND_BOTTOM)
    // ========================================================================
    property var desktopWindow: Window {
        id: deskWin
        visible: true
        title: "KWin-Win Desktop"
        flags: Qt.FramelessWindowHint
        x: 0
        y: 0
        width: Screen.width
        height: Screen.height

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

            // Plasma Desktop Header / Watermark Widget
            ColumnLayout {
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 40
                spacing: 4

                Text {
                    Layout.alignment: Qt.AlignRight
                    text: Qt.formatDateTime(new Date(), "h:mm ap")
                    font.pixelSize: 64
                    font.weight: Font.Light
                    color: "#e6eff0f1"
                }

                Text {
                    Layout.alignment: Qt.AlignRight
                    text: Qt.formatDateTime(new Date(), "dddd, MMMM d, yyyy")
                    font.pixelSize: 18
                    font.weight: Font.Normal
                    color: "#993daee9"
                }

                Text {
                    Layout.alignment: Qt.AlignRight
                    Layout.topMargin: 8
                    text: "KDE Plasma 6 on Windows 10/11"
                    font.pixelSize: 12
                    font.weight: Font.DemiBold
                    color: "#55eff0f1"
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
                    onTriggered: {
                        menuWin.visible = !menuWin.visible;
                    }
                }
                MenuItem {
                    text: "💻 Open Terminal"
                    onTriggered: trayBridge.sendTrayClick(0, 1003, 1)
                }
                MenuItem {
                    text: "📁 Open File Manager"
                    onTriggered: trayBridge.sendTrayClick(0, 1002, 1)
                }
                MenuSeparator {}
                MenuItem {
                    text: "🔄 Refresh Applications"
                    onTriggered: appModel.reloadApplications()
                }
            }
        }
    }

    // ========================================================================
    // 2. Floating KDE Plasma 6 Bottom Taskbar Panel Window (HWND_TOPMOST)
    // ========================================================================
    property var taskbarWindow: Window {
        id: barWin
        visible: true
        title: "KWin-Win Taskbar"
        flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        color: "transparent"

        // Docked to bottom, slightly floating with 6px margin
        x: 8
        y: Screen.height - 54
        width: Screen.width - 16
        height: 48

        TaskbarPanel {
            id: panelItem
            anchors.fill: parent
            radius: 10

            onKickoffClicked: {
                menuWin.visible = !menuWin.visible;
                if (menuWin.visible) {
                    menuWin.requestActivate();
                }
            }

            onShowDesktopClicked: {
                for (var i = 0; i < windowManagerModel.rowCount(); ++i) {
                    var idx = windowManagerModel.index(i, 0);
                    var hwnd = windowManagerModel.data(idx, 0x0101);
                    windowManagerModel.toggleMinimize(hwnd);
                }
            }
        }
    }

    // ========================================================================
    // 3. Kickoff Application Menu Popup Window
    // ========================================================================
    property var menuWindow: Window {
        id: menuWin
        visible: false
        title: "KWin-Win Kickoff"
        flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Popup
        color: "transparent"

        width: 640
        height: 540
        x: 12
        y: Screen.height - 54 - 540 - 8

        KdeMenu {
            id: kdeMenuItem
            anchors.fill: parent

            onAppLaunched: {
                menuWin.visible = false;
            }
        }
    }
}
