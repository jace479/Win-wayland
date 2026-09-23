function populatePanel(p, screenIdx) {
    p.screen = screenIdx;
    p.location = "bottom";
    p.height = 44;
    p.alignment = "center";
    p.addWidget("org.kde.plasma.kickoff");
    p.addWidget("org.ntkde.taskbar");
    p.addWidget("org.kde.plasma.marginsseparator");
    p.addWidget("org.kde.plasma.systemtray");
    p.addWidget("org.kde.plasma.digitalclock");
    p.addWidget("org.kde.plasma.showdesktop");
}

var allPanels = panels();
var seenScreens = {};

// 1. Remove duplicate panels on the same screen
for (var i = allPanels.length - 1; i >= 0; --i) {
    var p = allPanels[i];
    var scr = p.screen;
    if (scr === undefined || scr === null || scr < 0) {
        scr = 0;
        p.screen = 0;
    }
    if (seenScreens[scr]) {
        print("Removing duplicate panel " + p.id + " on screen " + scr);
        p.remove();
    } else {
        seenScreens[scr] = p;
    }
}

// 2. Configure the remaining panel on each screen
for (var s in seenScreens) {
    var panel = seenScreens[s];
    panel.location = "bottom";
    panel.alignment = "center";
    panel.height = 44;

    var widgetIds = panel.widgetIds || [];
    var hasKickoff = false;
    var hasNtkdeTaskbar = false;

    for (var j = 0; j < widgetIds.length; ++j) {
        var w = panel.widgetById(widgetIds[j]);
        if (!w) continue;
        if (w.type === "org.kde.plasma.kickoff") {
            hasKickoff = true;
        }
        if (w.type === "org.ntkde.taskbar") {
            hasNtkdeTaskbar = true;
        }
    }

    if (!hasNtkdeTaskbar) {
        var swapped = false;
        for (var k = 0; k < widgetIds.length; ++k) {
            var oldW = panel.widgetById(widgetIds[k]);
            if (oldW && (oldW.type === "org.kde.plasma.icontasks" || oldW.type === "org.kde.plasma.taskmanager")) {
                oldW.remove();
                panel.addWidget("org.ntkde.taskbar");
                swapped = true;
                break;
            }
        }
        if (!swapped) {
            panel.addWidget("org.ntkde.taskbar");
        }
    }
}

// 3. If screen 0 had no panel at all, create exactly one
if (!seenScreens[0]) {
    var p0 = new Panel("org.kde.panel");
    populatePanel(p0, 0);
}
