import QtQuick
import QtQuick.Controls

Window {
    id: kickoffWindow
    title: "KWin-Win Kickoff"
    flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
    color: "transparent"
    width: 640
    height: 540
    visible: false

    property int menuX: 12
    property int menuY: 480

    x: menuX
    y: menuY

    KdeMenu {
        id: menuContent
        anchors.fill: parent
        onAppLaunched: {
            kickoffWindow.visible = false
        }
    }

    property bool wasActivated: false

    function toggle() {
        if (visible) {
            visible = false;
            wasActivated = false;
        } else {
            wasActivated = false;
            menuContent.resetFilters();
            visible = true;
            raise();
            requestActivate();
        }
    }

    function openAt(posX, posY) {
        x = posX;
        y = posY;
        wasActivated = false;
        menuContent.resetFilters();
        visible = true;
        raise();
        requestActivate();
    }

    onActiveChanged: {
        if (active) {
            wasActivated = true;
        } else if (wasActivated && visible) {
            visible = false;
            wasActivated = false;
        }
    }
}
