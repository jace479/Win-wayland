import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: taskbarRoot
    height: 48
    color: "#eb232629" // Breeze Dark Translucent (92% opacity)
    border.color: "#31363b"
    border.width: 1

    signal kickoffClicked()
    signal showDesktopClicked()

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 8
        anchors.rightMargin: 8
        spacing: 8

        // Kickoff Application Launcher Button
        Rectangle {
            id: kickoffBtn
            Layout.preferredWidth: 38
            Layout.preferredHeight: 38
            radius: 6
            color: kickoffMouse.containsMouse ? "#31363b" : "transparent"
            border.color: kickoffMouse.containsMouse ? "#3daee9" : "transparent"
            border.width: 1

            // KDE Gear / Plasma stylized icon
            Text {
                anchors.centerIn: parent
                text: "⚙"
                font.pixelSize: 22
                color: kickoffMouse.containsMouse ? "#3daee9" : "#eff0f1"
            }

            MouseArea {
                id: kickoffMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: taskbarRoot.kickoffClicked()
            }
        }

        // Separator
        Rectangle {
            Layout.preferredWidth: 1
            Layout.preferredHeight: 24
            color: "#31363b"
        }

        // Icon-Only Task Manager (Running Managed Windows)
        ListView {
            id: taskManagerList
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: ListView.Horizontal
            spacing: 4
            clip: true
            model: windowManagerModel

            delegate: Rectangle {
                id: taskItemDelegate
                width: 44
                height: 38
                anchors.verticalCenter: parent ? parent.verticalCenter : undefined
                radius: 6
                color: model.isActive ? "#2a3744" : (taskMouse.containsMouse ? "#31363b" : "transparent")
                border.color: model.isActive ? "#3daee9" : "transparent"
                border.width: 1

                Image {
                    anchors.centerIn: parent
                    width: 26
                    height: 26
                    source: model.iconUrl
                    fillMode: Image.PreserveAspectFit
                    asynchronous: true
                }

                // Active glowing indicator pill at bottom
                Rectangle {
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: 2
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: model.isActive ? 20 : (model.isMinimized ? 6 : 12)
                    height: 3
                    radius: 1.5
                    color: model.isActive ? "#3daee9" : "#7f8c8d"
                    visible: true
                }

                // Tooltip showing window title
                ToolTip {
                    visible: taskMouse.containsMouse
                    text: model.windowTitle
                    delay: 400
                }

                MouseArea {
                    id: taskMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    acceptedButtons: Qt.LeftButton | Qt.RightButton
                    cursorShape: Qt.PointingHandCursor

                    onClicked: (mouse) => {
                        if (mouse.button === Qt.LeftButton) {
                            windowManagerModel.toggleMinimize(model.hwnd);
                        } else if (mouse.button === Qt.RightButton) {
                            taskContextMenu.popup();
                        }
                    }

                    Menu {
                        id: taskContextMenu
                        MenuItem {
                            text: model.isMaximized ? "Restore" : "Maximize"
                            onTriggered: windowManagerModel.toggleMaximize(model.hwnd)
                        }
                        MenuItem {
                            text: "Minimize"
                            onTriggered: windowManagerModel.toggleMinimize(model.hwnd)
                        }
                        MenuSeparator {}
                        MenuItem {
                            text: "Close"
                            onTriggered: windowManagerModel.closeWindow(model.hwnd)
                        }
                    }
                }
            }
        }

        // Separator
        Rectangle {
            Layout.preferredWidth: 1
            Layout.preferredHeight: 24
            color: "#31363b"
        }

        // System Tray Widget
        Row {
            id: systemTrayRow
            Layout.alignment: Qt.AlignVCenter
            spacing: 4

            Repeater {
                model: trayModel

                delegate: Rectangle {
                    width: 28
                    height: 28
                    radius: 4
                    color: trayItemMouse.containsMouse ? "#31363b" : "transparent"

                    Image {
                        anchors.centerIn: parent
                        width: 20
                        height: 20
                        source: model.trayIcon
                        fillMode: Image.PreserveAspectFit
                    }

                    ToolTip {
                        visible: trayItemMouse.containsMouse && (model.toolTip !== "")
                        text: model.toolTip
                        delay: 400
                    }

                    MouseArea {
                        id: trayItemMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        acceptedButtons: Qt.LeftButton | Qt.RightButton
                        cursorShape: Qt.PointingHandCursor

                        onClicked: (mouse) => {
                            if (mouse.button === Qt.LeftButton) {
                                trayBridge.sendTrayClick(model.clientHwnd, model.trayId, 1);
                            } else if (mouse.button === Qt.RightButton) {
                                trayBridge.sendTrayClick(model.clientHwnd, model.trayId, 2);
                            }
                        }

                        onDoubleClicked: {
                            trayBridge.sendTrayClick(model.clientHwnd, model.trayId, 3);
                        }
                    }
                }
            }
        }

        // Separator
        Rectangle {
            Layout.preferredWidth: 1
            Layout.preferredHeight: 24
            color: "#31363b"
        }

        // Digital Clock & Date Widget
        Rectangle {
            id: clockWidget
            Layout.preferredWidth: 95
            Layout.fillHeight: true
            color: clockMouse.containsMouse ? "#2a2d31" : "transparent"
            radius: 6

            ColumnLayout {
                anchors.centerIn: parent
                spacing: 1

                Text {
                    id: clockTime
                    Layout.alignment: Qt.AlignHCenter
                    text: Qt.formatDateTime(new Date(), "h:mm ap")
                    color: "#eff0f1"
                    font.pixelSize: 12
                    font.weight: Font.DemiBold
                }

                Text {
                    id: clockDate
                    Layout.alignment: Qt.AlignHCenter
                    text: Qt.formatDateTime(new Date(), "MMM d, yyyy")
                    color: "#7f8c8d"
                    font.pixelSize: 10
                }
            }

            Timer {
                interval: 1000
                running: true
                repeat: true
                onTriggered: {
                    var now = new Date();
                    clockTime.text = Qt.formatDateTime(now, "h:mm ap");
                    clockDate.text = Qt.formatDateTime(now, "MMM d, yyyy");
                }
            }

            MouseArea {
                id: clockMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
            }
        }

        // Show Desktop Peek Button (Far Right)
        Rectangle {
            id: showDesktopBtn
            Layout.preferredWidth: 12
            Layout.fillHeight: true
            Layout.margins: 2
            radius: 2
            color: showDesktopMouse.containsMouse ? "#3daee9" : "#31363b"

            MouseArea {
                id: showDesktopMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: taskbarRoot.showDesktopClicked()
            }
        }
    }
}
