import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: decoRoot

    required property var model
    visible: model.isVisible && !model.isMinimized

    x: model.windowX
    y: Math.max(0, model.windowY - 30)
    width: model.windowWidth
    height: 30

    Rectangle {
        id: titlebarBackground
        anchors.fill: parent
        radius: model.isMaximized ? 0 : 6
        color: model.isActive ? "#eb232629" : "#d91d2023"
        border.color: model.isActive ? "#3daee9" : "#31363b"
        border.width: 1

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 8
            anchors.rightMargin: 4
            spacing: 6

            // App Icon
            Image {
                Layout.preferredWidth: 18
                Layout.preferredHeight: 18
                source: model.iconUrl
                fillMode: Image.PreserveAspectFit
                asynchronous: true
            }

            // Window Title Text
            Text {
                Layout.fillWidth: true
                text: model.windowTitle
                color: model.isActive ? "#eff0f1" : "#7f8c8d"
                font.pixelSize: 11
                font.weight: model.isActive ? Font.DemiBold : Font.Normal
                elide: Text.ElideRight
            }

            // Window Control Buttons (KDE Breeze Style)
            // Minimize
            Rectangle {
                Layout.preferredWidth: 26
                Layout.preferredHeight: 22
                radius: 4
                color: minMouse.containsMouse ? "#31363b" : "transparent"

                Text {
                    anchors.centerIn: parent
                    text: "─"
                    color: "#eff0f1"
                    font.pixelSize: 10
                }

                MouseArea {
                    id: minMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: windowManagerModel.toggleMinimize(model.hwnd)
                }
            }

            // Maximize / Restore
            Rectangle {
                Layout.preferredWidth: 26
                Layout.preferredHeight: 22
                radius: 4
                color: maxMouse.containsMouse ? "#31363b" : "transparent"

                Text {
                    anchors.centerIn: parent
                    text: model.isMaximized ? "❐" : "□"
                    color: "#eff0f1"
                    font.pixelSize: 11
                }

                MouseArea {
                    id: maxMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: windowManagerModel.toggleMaximize(model.hwnd)
                }
            }

            // Close
            Rectangle {
                id: closeBtn
                Layout.preferredWidth: 26
                Layout.preferredHeight: 22
                radius: 4
                color: closeMouse.containsMouse ? "#da4453" : "transparent"

                Text {
                    anchors.centerIn: parent
                    text: "✕"
                    color: closeMouse.containsMouse ? "#ffffff" : "#eff0f1"
                    font.pixelSize: 11
                }

                MouseArea {
                    id: closeMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: windowManagerModel.closeWindow(model.hwnd)
                }
            }
        }

        // Drag handler / click to activate
        MouseArea {
            anchors.left: parent.left
            anchors.right: closeBtn.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            onPressed: windowManagerModel.activateWindow(model.hwnd)
            onDoubleClicked: windowManagerModel.toggleMaximize(model.hwnd)
        }
    }
}
