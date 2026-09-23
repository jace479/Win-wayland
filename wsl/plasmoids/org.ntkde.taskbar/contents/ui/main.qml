import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import QtCore
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.components as PlasmaComponents3
import org.kde.kirigami as Kirigami
import org.kde.plasma.plasma5support as Plasma5Support

PlasmoidItem {
    id: root

    preferredRepresentation: fullRepresentation
    Layout.fillWidth: true
    Layout.fillHeight: true
    Layout.minimumWidth: 40

    property var tasksModel: []
    property bool fullscreenActive: false
    readonly property string stateDir: {
        var s = "" + StandardPaths.writableLocation(StandardPaths.GenericStateLocation);
        if (s.indexOf("file://") === 0) {
            s = s.substring(7);
        }
        if (!s || s.length === 0 || s === "undefined") {
            s = "/home/jace479/.local/state";
        }
        return s + "/nt-plasma";
    }
    readonly property string actionScript: "/mnt/d/WinKDE/wsl/send-action.py"

    Plasma5Support.DataSource {
        id: runner
        engine: "executable"
        connectedSources: []
        onNewData: function(sourceName, data) {
            disconnectSource(sourceName);
        }
    }

    function dispatchAction(action, hwnd) {
        var h = (hwnd !== undefined && hwnd !== null) ? hwnd : 0;
        var cmd = "python3 " + actionScript + " " + action + " " + h + " #" + Date.now();
        runner.disconnectSource(cmd);
        runner.connectSource(cmd);
    }

    property string lastJson: ""

    function fetchTasks() {
        var xhr = new XMLHttpRequest();
        var url = "file://" + stateDir + "/tasks.json?t=" + Date.now();
        xhr.open("GET", url);
        xhr.onreadystatechange = function() {
            if (xhr.readyState === XMLHttpRequest.DONE && (xhr.status === 200 || xhr.status === 0)) {
                if (xhr.responseText && xhr.responseText.length > 0) {
                    if (xhr.responseText !== root.lastJson) {
                        root.lastJson = xhr.responseText;
                        try {
                            var parsed = JSON.parse(xhr.responseText);
                            if (Array.isArray(parsed)) {
                                root.tasksModel = parsed;
                            }
                        } catch (e) {
                        }
                    }
                }
            }
        };
        xhr.send();
    }

    function fetchFullscreen() {
        var xhr = new XMLHttpRequest();
        var url = "file://" + stateDir + "/fullscreen.json?t=" + Date.now();
        xhr.open("GET", url);
        xhr.onreadystatechange = function() {
            if (xhr.readyState === XMLHttpRequest.DONE && (xhr.status === 200 || xhr.status === 0)) {
                if (xhr.responseText && xhr.responseText.length > 0) {
                    try {
                        var parsed = JSON.parse(xhr.responseText);
                        root.fullscreenActive = (parsed.fullscreen === true);
                    } catch (e) {
                    }
                }
            }
        };
        xhr.send();
    }

    Component.onCompleted: {
        fetchTasks();
    }

    Timer {
        id: pollTimer
        interval: 500
        running: true
        repeat: true
        onTriggered: {
            fetchTasks();
            fetchFullscreen();
        }
    }

    fullRepresentation: Item {
        id: container
        anchors.fill: parent
        visible: !root.fullscreenActive
        opacity: root.fullscreenActive ? 0.0 : 1.0

        Behavior on opacity {
            NumberAnimation { duration: 200 }
        }
        ListView {
            id: taskListView
            anchors.fill: parent
            anchors.margins: 2
            orientation: ListView.Horizontal
            spacing: 4
            clip: true
            model: root.tasksModel

            delegate: Rectangle {
                id: taskDelegate
                required property var modelData

                // Square tile for Icons-Only Task Manager
                width: height
                height: taskListView.height
                radius: 4

                readonly property bool isActive: modelData.active === true
                readonly property bool isMinimized: modelData.minimized === true

                color: {
                    if (taskMouse.pressed) {
                        return Qt.rgba(Kirigami.Theme.highlightColor.r, Kirigami.Theme.highlightColor.g, Kirigami.Theme.highlightColor.b, 0.38);
                    }
                    if (isActive) {
                        return Qt.rgba(Kirigami.Theme.highlightColor.r, Kirigami.Theme.highlightColor.g, Kirigami.Theme.highlightColor.b, 0.22);
                    }
                    if (taskMouse.containsMouse) {
                        return Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g, Kirigami.Theme.textColor.b, 0.12);
                    }
                    return "transparent";
                }

                border.color: {
                    if (isActive) {
                        return Qt.rgba(Kirigami.Theme.highlightColor.r, Kirigami.Theme.highlightColor.g, Kirigami.Theme.highlightColor.b, 0.50);
                    }
                    if (taskMouse.containsMouse) {
                        return Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g, Kirigami.Theme.textColor.b, 0.18);
                    }
                    return "transparent";
                }
                border.width: 1

                opacity: isMinimized ? 0.60 : 1.0

                Behavior on opacity {
                    NumberAnimation { duration: 150 }
                }

                // Centered App Icon
                Kirigami.Icon {
                    id: taskIcon
                    anchors.centerIn: parent
                    width: Math.min(32, Math.max(22, taskDelegate.height - 12))
                    height: width
                    source: {
                        var ic = modelData.icon || "application-x-executable";
                        if (ic.indexOf("/") === 0) {
                            return "file://" + ic;
                        }
                        return ic;
                    }
                    fallback: "application-x-executable"
                }

                // Active indicator pill at bottom (matching KDE Breeze icontasks)
                Rectangle {
                    id: activeIndicator
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: 2
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: Math.max(14, parent.width * 0.55)
                    height: 3
                    radius: 1.5
                    color: Kirigami.Theme.highlightColor
                    visible: taskDelegate.isActive
                }

                // Subtle hover indicator bar when not active
                Rectangle {
                    id: hoverIndicator
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: 2
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: Math.max(8, parent.width * 0.25)
                    height: 2
                    radius: 1
                    color: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g, Kirigami.Theme.textColor.b, 0.40)
                    visible: !taskDelegate.isActive && taskMouse.containsMouse
                }

                MouseArea {
                    id: taskMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    acceptedButtons: Qt.LeftButton | Qt.MiddleButton | Qt.RightButton

                    onClicked: function(mouse) {
                        if (mouse.button === Qt.LeftButton) {
                            // Host natively toggles: active window minimizes, background/minimized window activates
                            root.dispatchAction("toggle", modelData.hwnd);
                        } else if (mouse.button === Qt.MiddleButton) {
                            root.dispatchAction("close", modelData.hwnd);
                        } else if (mouse.button === Qt.RightButton) {
                            contextMenu.popup();
                        }
                    }
                }

                PlasmaComponents3.ToolTip {
                    visible: taskMouse.containsMouse
                    text: (modelData.title || "Windows Application") + (modelData.process ? ("\n(" + modelData.process + ")") : "")
                }

                PlasmaComponents3.Menu {
                    id: contextMenu

                    PlasmaComponents3.MenuItem {
                        text: taskDelegate.isMinimized ? "Restore" : "Activate"
                        icon.name: "window"
                        onClicked: root.dispatchAction("activate", modelData.hwnd)
                    }

                    PlasmaComponents3.MenuItem {
                        text: "Minimize"
                        icon.name: "window-minimize"
                        onClicked: root.dispatchAction("minimize", modelData.hwnd)
                    }

                    PlasmaComponents3.MenuSeparator {}

                    PlasmaComponents3.MenuItem {
                        text: "Close"
                        icon.name: "window-close"
                        onClicked: root.dispatchAction("close", modelData.hwnd)
                    }
                }
            }
        }
    }
}
