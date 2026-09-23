import QtQuick
import QtQuick.Controls

Window {
    id: taskbarWindow
    visible: true
    title: "KWin-Win Taskbar"
    flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
    color: "transparent"

    property int screenX: 0
    property int screenY: 0
    property int screenW: (typeof screenWidth !== "undefined" && screenWidth > 0) ? screenWidth : Screen.width
    property int screenH: (typeof screenHeight !== "undefined" && screenHeight > 0) ? screenHeight : Screen.height

    // Floating panel docked at the bottom of the display
    x: screenX + 8
    y: screenY + screenH - 56
    width: screenW - 16
    height: 48

    signal toggleKickoffRequested()

    TaskbarPanel {
        id: panel
        anchors.fill: parent
        radius: 10

        onKickoffClicked: {
            taskbarWindow.toggleKickoffRequested()
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
