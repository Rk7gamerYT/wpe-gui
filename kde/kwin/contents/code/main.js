// KWin 6: only visible windows on the current desktop/activity count.
function report() {
    var covered = {fullscreen: [], maximized: []};
    if (!workspace.showingDesktop) {
        workspace.stackingOrder.forEach(function(w) {
            if (!w.normalWindow || w.minimized || w.deleted || !w.output) return;
            // Layer-shell render surfaces can also report normalWindow in KWin.
            var identity = String(w.resourceClass) + " " + String(w.caption);
            if (/wallpaperengine|linux-wallpaperengine/i.test(identity)) return;
            if (w.desktops.length && w.desktops.indexOf(workspace.currentDesktop) < 0) return;
            if (w.activities.length && w.activities.indexOf(workspace.currentActivity) < 0) return;
            var screen = w.output.geometry;
            var frame = w.frameGeometry;
            var area = workspace.clientArea(KWin.MaximizeArea, w.output, workspace.currentDesktop);
            var rect = [screen.x, screen.y, screen.width, screen.height];
            if (w.fullScreen) covered.fullscreen.push(rect);
            else if (frame.x <= area.x + 1 && frame.y <= area.y + 1 &&
                     frame.x + frame.width >= area.x + area.width - 1 &&
                     frame.y + frame.height >= area.y + area.height - 1)
                covered.maximized.push(rect);
        });
    }
    callDBus("org.wpegui.KWin", "/org/wpegui/KWin", "org.wpegui.KWin",
             "ReportCovered", JSON.stringify(covered));
}
function watch(w) {
    ["frameGeometryChanged", "fullScreenChanged", "minimizedChanged", "desktopsChanged",
     "activitiesChanged", "outputChanged"].forEach(function(name) {
        if (w[name]) w[name].connect(report);
    });
    report();
}
workspace.stackingOrder.forEach(watch);
workspace.windowAdded.connect(watch);
workspace.windowRemoved.connect(report);
workspace.windowActivated.connect(report);
workspace.currentDesktopChanged.connect(report);
workspace.currentActivityChanged.connect(report);
workspace.screensChanged.connect(report);
if (workspace.showingDesktopChanged) workspace.showingDesktopChanged.connect(report);
report();
