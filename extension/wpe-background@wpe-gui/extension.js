import GLib from 'gi://GLib';
import {Extension, InjectionManager} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as Workspace from 'resource:///org/gnome/shell/ui/workspace.js';

// Window title/class used by linux-wallpaperengine (GLFW)
const TITLE = 'wallpaperengine';

const isEngine = win =>
    win && (win.get_title() === TITLE || win.get_wm_class() === 'linux-wallpaperengine');

export default class WpeBackground extends Extension {
    enable() {
        this._pinned = new Map(); // actor -> signal ids to undo
        this._injections = new InjectionManager();

        // Keep the wallpaper window out of the Activities overview
        const proto = Workspace.Workspace?.prototype;
        if (typeof proto?._isOverviewWindow === 'function') {
            this._injections.overrideMethod(proto, '_isOverviewWindow', original =>
                function (window) {
                    const meta = window.get_meta_window?.() ?? window;
                    return isEngine(meta) ? false : original.call(this, window);
                });
        } else {
            console.warn('[wpe-background] Workspace._isOverviewWindow not found; window will show in the overview');
        }

        // GNOME rebuilds the per-monitor backgrounds from time to time and the new
        // background actors land on top of ours; raise the wallpaper again when it happens.
        const bg = Main.layoutManager._backgroundGroup;
        this._childAddedId = bg.connect('child-added', (_g, child) => {
            console.log(`[wpe-background] child-added: ${child.constructor.name}`);
            this._raiseAllLater();
        });

        // Mutter restacks every window actor whenever any window changes and, for ours (the lowest one),
        // pushes it under the shell's own background actor. Raise it again after each restack.
        this._restackId = global.display.connect('restacked', () => this._raiseAllLater());
        this._monitorsId = Main.layoutManager.connect('monitors-changed', () => {
            for (const actor of this._pinned.keys())
                this._place(actor);
        });
        this._mapId = global.window_manager.connect('map', (_wm, actor) => this._maybePin(actor));
        global.get_window_actors().forEach(a => this._maybePin(a));
    }

    disable() {
        global.window_manager.disconnect(this._mapId);
        Main.layoutManager.disconnect(this._monitorsId);
        global.display.disconnect(this._restackId);
        Main.layoutManager._backgroundGroup.disconnect(this._childAddedId);
        if (this._raiseTimeout) {
            GLib.source_remove(this._raiseTimeout);
            this._raiseTimeout = null;
        }
        this._injections.clear();
        this._injections = null;
        for (const [actor, ids] of this._pinned) {
            const win = actor.meta_window;
            if (win)
                ids.win.forEach(id => win.disconnect(id));
            ids.actor.forEach(id => actor.disconnect(id));
        }
        this._pinned = null;
    }

    _raiseAllLater() {
        if (this._raiseTimeout)
            return;
        this._raiseTimeout = GLib.idle_add(GLib.PRIORITY_DEFAULT, () => {
            this._raiseTimeout = null;
            for (const actor of this._pinned.keys())
                this._toBackground(actor);
            return GLib.SOURCE_REMOVE;
        });
    }

    _toBackground(actor) {
        const bg = Main.layoutManager._backgroundGroup;
        if (actor.get_parent() !== bg) {
            console.log('[wpe-background] moving window actor to background group');
            actor.get_parent()?.remove_child(actor);
            bg.add_child(actor);
        } else if (bg.get_last_child() !== actor) {
            console.log('[wpe-background] raising window actor above the new backgrounds');
            bg.set_child_above_sibling(actor, null);
        }
        actor.reactive = false;
        actor.show();
    }

    // Mutter keeps normal windows out of the top bar's strut, which pushes the wallpaper 32px down.
    // The actor lives in the background group, so we can simply pin it to the monitor's corner.
    _place(actor) {
        const info = this._pinned.get(actor);
        if (!info)
            return;
        const monitor = Main.layoutManager.monitors[info.monitor];
        if (!monitor)
            return;
        if (actor.x !== monitor.x || actor.y !== monitor.y) {
            info.placing = true;
            actor.set_position(monitor.x, monitor.y);
            info.placing = false;
        }
    }

    _describe(actor) {
        const bg = Main.layoutManager._backgroundGroup;
        const kids = bg.get_children().map(c => c.constructor.name).join(',');
        return `pos=${actor.x},${actor.y} size=${actor.width}x${actor.height} visible=${actor.visible} ` +
            `mapped=${actor.mapped} opacity=${actor.opacity} parentIsBg=${actor.get_parent() === bg} children=[${kids}]`;
    }

    _maybePin(actor) {
        const win = actor.meta_window;
        if (!isEngine(win))
            return;

        // The window mapped again (e.g. after a minimize): make sure it is still in the background
        if (this._pinned.has(actor)) {
            console.log('[wpe-background] window mapped again, re-pinning');
            this._toBackground(actor);
            return;
        }

        const monitor = Main.layoutManager.monitors[win.get_monitor()];
        console.log(`[wpe-background] pinning "${win.get_title()}" on monitor ${win.get_monitor()}`);
        win.stick();
        win.move_resize_frame(false, monitor.x, monitor.y, monitor.width, monitor.height);
        this._toBackground(actor);

        // A wallpaper must never stay minimized or hidden
        const winIds = [
            win.connect('notify::minimized', () => {
                console.log(`[wpe-background] notify::minimized -> ${win.minimized}`);
                if (win.minimized)
                    win.unminimize();
            }),
        ];
        const actorIds = [
            actor.connect('notify::visible', () => {
                if (!actor.visible) {
                    console.log('[wpe-background] actor was hidden, showing again');
                    actor.show();
                }
            }),
            actor.connect('destroy', () => this._pinned?.delete(actor)),
        ];
        this._pinned.set(actor, {win: winIds, actor: actorIds, monitor: win.get_monitor(), placing: false});
        this._place(actor);
        actorIds.push(actor.connect('notify::position', () => {
            if (!this._pinned?.get(actor)?.placing)
                this._place(actor);
        }));

        if (win.minimized)
            win.unminimize();

        // State dump, to debug wallpapers that don't show up
        GLib.timeout_add(GLib.PRIORITY_DEFAULT, 1500, () => {
            if (this._pinned?.has(actor))
                console.log(`[wpe-background] state: ${this._describe(actor)}`);
            return GLib.SOURCE_REMOVE;
        });
    }
}
