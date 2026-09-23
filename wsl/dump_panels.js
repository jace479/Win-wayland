var allPanels = panels();
for (var i = 0; i < allPanels.length; ++i) {
    var p = allPanels[i];
    var w = p.widgets();
    var wtypes = [];
    for (var j = 0; j < w.length; ++j) {
        wtypes.push(w[j].type);
    }
    print("Panel " + i + " screen " + p.screen + " location " + p.location + " height " + p.height + ": " + wtypes.join(", "));
}
