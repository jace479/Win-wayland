import QtQuick
import org.kde.plasma.plasma5support as Plasma5Support

Item {
    width: 400
    height: 300

    Plasma5Support.DataSource {
        id: fileReader
        engine: "executable"
        connectedSources: []
        onNewData: function(sourceName, data) {
            console.log("onNewData called for:", sourceName);
            console.log("stdout:", data["stdout"]);
            console.log("keys:", Object.keys(data));
            disconnectSource(sourceName);
        }
    }

    Component.onCompleted: {
        console.log("Component completed, connecting source...");
        fileReader.connectSource("cat /home/jace479/.local/state/nt-plasma/tasks.json");
    }
}
