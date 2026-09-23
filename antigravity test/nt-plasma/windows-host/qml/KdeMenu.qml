import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: kdeMenuRoot
    width: 640
    height: 540
    radius: 12
    color: "#e6232629" // Breeze Dark Translucent (90% opacity)
    border.color: "#3daee9" // KDE Neon Blue Accent
    border.width: 1

    property string selectedCategory: "All Applications"
    property string searchQuery: ""

    signal appLaunched()

    function resetFilters() {
        selectedCategory = "All Applications";
        searchQuery = "";
        searchInput.text = "";
        appModel.categoryFilter = "All Applications";
        appModel.searchFilter = "";
        searchInput.forceActiveFocus();
    }

    // Shadow effect simulation
    Rectangle {
        anchors.fill: parent
        anchors.margins: -4
        radius: 14
        color: "transparent"
        border.color: "#33000000"
        border.width: 4
        z: -1
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 12

        // Search Bar at Top
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 38
            color: "#1d2023"
            radius: 8
            border.color: searchInput.activeFocus ? "#3daee9" : "#31363b"
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                spacing: 8

                Text {
                    text: "🔍"
                    color: "#7f8c8d"
                    font.pixelSize: 14
                }

                TextInput {
                    id: searchInput
                    Layout.fillWidth: true
                    color: "#eff0f1"
                    font.pixelSize: 13
                    selectByMouse: true
                    clip: true
                    onTextChanged: {
                        kdeMenuRoot.searchQuery = text.trim().toLowerCase();
                        appModel.searchFilter = text.trim();
                    }

                    Text {
                        anchors.fill: parent
                        text: "Type to search applications..."
                        color: "#7f8c8d"
                        font.pixelSize: 13
                        visible: !searchInput.text && !searchInput.activeFocus
                    }
                }

                Text {
                    text: "✕"
                    color: "#7f8c8d"
                    font.pixelSize: 12
                    visible: searchInput.text.length > 0
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            searchInput.text = "";
                            appModel.searchFilter = "";
                        }
                    }
                }
            }
        }

        // Two-Column Content: Categories (Left) & Application Grid (Right)
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 12

            // Left Category Navigation
            Rectangle {
                Layout.preferredWidth: 160
                Layout.fillHeight: true
                color: "#1a1d20"
                radius: 8
                border.color: "#31363b"
                border.width: 1

                ListView {
                    id: categoryList
                    anchors.fill: parent
                    anchors.margins: 6
                    clip: true
                    model: appModel.categories
                    spacing: 2

                    delegate: Rectangle {
                        id: catDelegate
                        width: categoryList.width - 12
                        height: 36
                        radius: 6
                        color: kdeMenuRoot.selectedCategory === modelData ? "#2a3744" : (catMouse.containsMouse ? "#25282c" : "transparent")
                        border.color: kdeMenuRoot.selectedCategory === modelData ? "#3daee9" : "transparent"
                        border.width: 1

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 10
                            anchors.rightMargin: 10
                            spacing: 8

                            Text {
                                text: {
                                    if (modelData === "All Applications") return "📁";
                                    if (modelData === "Development") return "💻";
                                    if (modelData === "Games") return "🎮";
                                    if (modelData === "Graphics") return "🎨";
                                    if (modelData === "Internet") return "🌐";
                                    if (modelData === "Multimedia") return "🎵";
                                    if (modelData === "Office") return "📄";
                                    if (modelData === "System") return "⚙️";
                                    if (modelData === "Utilities") return "🔧";
                                    return "📦";
                                }
                                font.pixelSize: 14
                            }

                            Text {
                                Layout.fillWidth: true
                                text: modelData
                                color: kdeMenuRoot.selectedCategory === modelData ? "#3daee9" : "#eff0f1"
                                font.pixelSize: 12
                                font.weight: kdeMenuRoot.selectedCategory === modelData ? Font.DemiBold : Font.Normal
                                elide: Text.ElideRight
                            }
                        }

                        MouseArea {
                            id: catMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                kdeMenuRoot.selectedCategory = modelData;
                                appModel.categoryFilter = modelData;
                                searchInput.text = "";
                                appModel.searchFilter = "";
                            }
                        }
                    }
                }
            }

            // Right Application Grid / List
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: "#1a1d20"
                radius: 8
                border.color: "#31363b"
                border.width: 1

                GridView {
                    id: appGridView
                    anchors.fill: parent
                    anchors.margins: 8
                    clip: true
                    cellWidth: 140
                    cellHeight: 90

                    model: appModel

                    ScrollBar.vertical: ScrollBar {
                        active: true
                        policy: ScrollBar.AsNeeded
                    }

                    delegate: Item {
                        id: appItemDelegate
                        width: appGridView.cellWidth
                        height: appGridView.cellHeight

                        Rectangle {
                            anchors.fill: parent
                            anchors.margins: 4
                            radius: 8
                            color: appMouse.containsMouse ? "#2f3844" : "transparent"
                            border.color: appMouse.containsMouse ? "#3daee9" : "transparent"
                            border.width: 1

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 6
                                spacing: 4

                                Image {
                                    Layout.alignment: Qt.AlignHCenter
                                    Layout.preferredWidth: 36
                                    Layout.preferredHeight: 36
                                    source: model.iconUrl
                                    fillMode: Image.PreserveAspectFit
                                    asynchronous: true
                                }

                                Text {
                                    Layout.fillWidth: true
                                    Layout.alignment: Qt.AlignHCenter
                                    text: model.appName
                                    color: "#eff0f1"
                                    font.pixelSize: 11
                                    horizontalAlignment: Text.AlignHCenter
                                    elide: Text.ElideRight
                                    maximumLineCount: 2
                                    wrapMode: Text.Wrap
                                }
                            }

                            MouseArea {
                                id: appMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    appModel.launchById(model.appId);
                                    kdeMenuRoot.appLaunched();
                                }
                            }
                        }
                    }
                }

                // Empty state when filter yields zero results
                Text {
                    anchors.centerIn: parent
                    visible: appModel.count === 0
                    text: "No applications found"
                    color: "#7f8c8d"
                    font.pixelSize: 14
                }
            }
        }

        // Bottom Power & Session Bar
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 44
            color: "#181b1d"
            radius: 8
            border.color: "#31363b"
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                spacing: 8

                // User label
                Text {
                    text: "👤 Plasma User"
                    color: "#eff0f1"
                    font.pixelSize: 12
                    font.weight: Font.DemiBold
                }

                Item { Layout.fillWidth: true }

                // Lock button
                Rectangle {
                    width: 76
                    height: 28
                    radius: 4
                    color: lockMouse.containsMouse ? "#2f3844" : "#232629"
                    border.color: "#31363b"

                    Text {
                        anchors.centerIn: parent
                        text: "🔒 Lock"
                        color: "#eff0f1"
                        font.pixelSize: 11
                    }
                    MouseArea {
                        id: lockMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            appModel.launchById("win32_lock");
                            kdeMenuRoot.appLaunched();
                        }
                    }
                }

                // Restart button
                Rectangle {
                    width: 82
                    height: 28
                    radius: 4
                    color: restartMouse.containsMouse ? "#2f3844" : "#232629"
                    border.color: "#31363b"

                    Text {
                        anchors.centerIn: parent
                        text: "🔄 Restart"
                        color: "#eff0f1"
                        font.pixelSize: 11
                    }
                    MouseArea {
                        id: restartMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: kdeMenuRoot.appLaunched()
                    }
                }

                // Shutdown button
                Rectangle {
                    width: 90
                    height: 28
                    radius: 4
                    color: shutMouse.containsMouse ? "#da4453" : "#232629"
                    border.color: shutMouse.containsMouse ? "#ed1515" : "#31363b"

                    Text {
                        anchors.centerIn: parent
                        text: "⏻ Shut Down"
                        color: "#eff0f1"
                        font.pixelSize: 11
                    }
                    MouseArea {
                        id: shutMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: kdeMenuRoot.appLaunched()
                    }
                }
            }
        }
    }
}
