import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Meta from 'gi://Meta';
import {Extension, InjectionManager} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as Workspace from 'resource:///org/gnome/shell/ui/workspace.js';

// Window title/class used by linux-wallpaperengine (GLFW)
const TITLE = 'wallpaperengine';

const DBUS_NAME = 'org.wpegui.Background';
const DBUS_PATH = '/org/wpegui/Background';
const DBUS_XML = `<node><interface name="${DBUS_NAME}">
  <method name="GetCovered"><arg type="s" direction="out" name="json"/></method>
  <signal name="CoveredChanged"><arg type="s" name="json"/></signal>
</interface></node>`;

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
        this._childAddedId = bg.connect('child-added', () => {
            this._raiseAllLater();
        });

        // Mutter restacks every window actor whenever any window changes and, for ours (the lowest one),
        // pushes it under the shell's own background actor. Raise it again after each restack.
        this._restackId = global.display.connect('restacked', () => this._raiseAllLater());
        this._monitorsId = Main.layoutManager.connect('monitors-changed', () => {
            for (const [actor, info] of this._pinned) {
                info.target = this._targetFor(actor.meta_window);
                this._place(actor);
            }
        });
        this._mapId = global.window_manager.connect('map', (_wm, actor) => this._maybePin(actor));
        global.get_window_actors().forEach(a => this._maybePin(a));

        // Tell the app which monitors have a maximized or fullscreen window, so it can pause the wallpaper there
        this._coveredJson = '{"maximized":[],"fullscreen":[]}';
        this._dbus = Gio.DBusExportedObject.wrapJSObject(DBUS_XML, this);
        this._dbus.export(Gio.DBus.session, DBUS_PATH);
        this._busId = Gio.bus_own_name_on_connection(Gio.DBus.session, DBUS_NAME, Gio.BusNameOwnerFlags.NONE, null, null);
        this._coverageSignals = [
            [global.window_manager, ['map', 'destroy', 'minimize', 'unminimize', 'size-changed', 'switch-workspace']],
            [global.display, ['restacked', 'in-fullscreen-changed', 'window-entered-monitor', 'window-left-monitor']],
            [Main.layoutManager, ['monitors-changed']],
        ].flatMap(([obj, names]) => names.map(n => [obj, obj.connect(n, () => this._updateCoverageLater())]));
        this._updateCoverage();
    }

    GetCovered() {
        return this._coveredJson;
    }

    disable() {
        global.window_manager.disconnect(this._mapId);
        for (const [obj, id] of this._coverageSignals)
            obj.disconnect(id);
        this._coverageSignals = null;
        if (this._coverageTimeout) {
            GLib.source_remove(this._coverageTimeout);
            this._coverageTimeout = null;
        }
        this._dbus.unexport();
        this._dbus = null;
        Gio.bus_unown_name(this._busId);
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
            // Disconnect first: restoring reactivity must not trigger our guard.
            for (const [child, state] of ids.input)
                state.signals.forEach(id => child.disconnect(id));
            for (const [child, state] of ids.input)
                child.reactive = state.reactive;
            const win = actor.meta_window;
            if (win)
                ids.win.forEach(id => win.disconnect(id));
            ids.actor.forEach(id => actor.disconnect(id));
        }
        this._pinned = null;
    }

    _updateCoverageLater() {
        if (this._coverageTimeout)
            return;
        this._coverageTimeout = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 120, () => {
            this._coverageTimeout = null;
            this._updateCoverage();
            return GLib.SOURCE_REMOVE;
        });
    }

    // Monitors (as [x, y, width, height]) with a visible maximized / fullscreen window of an ordinary app
    _updateCoverage() {
        const monitors = Main.layoutManager.monitors;
        const workspace = global.workspace_manager.get_active_workspace();
        const maximized = new Set(), fullscreen = new Set();
        for (const actor of global.get_window_actors()) {
            const win = actor.meta_window;
            if (isEngine(win) || win.get_window_type() !== Meta.WindowType.NORMAL || win.minimized)
                continue;
            if (!win.located_on_workspace(workspace))
                continue;
            const monitor = win.get_monitor();
            if (win.is_fullscreen())
                fullscreen.add(monitor);
            if (win.maximized_horizontally && win.maximized_vertically)
                maximized.add(monitor);
        }
        const rects = set => [...set].filter(i => monitors[i])
            .map(i => [monitors[i].x, monitors[i].y, monitors[i].width, monitors[i].height]);
        const json = JSON.stringify({maximized: rects(maximized), fullscreen: rects(fullscreen)});
        if (json === this._coveredJson)
            return;
        this._coveredJson = json;
        console.log(`[wpe-background] covered: ${json}`);
        this._dbus?.emit_signal('CoveredChanged', new GLib.Variant('(s)', [json]));
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

    // Where a wallpaper window belongs: the app opens each window with exactly its monitor's size (or the
    // union of all monitors when spanning), but mutter moves new windows around (work area, other
    // monitors), so win.get_monitor() is unreliable. Match by size, then by distance.
    _targetFor(win) {
        const r = win.get_frame_rect();
        const monitors = Main.layoutManager.monitors;
        const candidates = monitors.map(m => ({x: m.x, y: m.y, width: m.width, height: m.height}));
        if (monitors.length > 1) {
            const x1 = Math.min(...monitors.map(m => m.x)), y1 = Math.min(...monitors.map(m => m.y));
            const x2 = Math.max(...monitors.map(m => m.x + m.width)), y2 = Math.max(...monitors.map(m => m.y + m.height));
            candidates.push({x: x1, y: y1, width: x2 - x1, height: y2 - y1}); // all monitors together
        }
        const fallback = monitors[win.get_monitor()] ?? monitors[0];
        if (r.width <= 1 || r.height <= 1)
            return {x: fallback.x, y: fallback.y};
        let best = candidates[0], bestScore = Infinity;
        for (const c of candidates) {
            const score = (Math.abs(c.width - r.width) + Math.abs(c.height - r.height)) * 1000 +
                Math.abs(c.x - r.x) + Math.abs(c.y - r.y);
            if (score < bestScore) {
                best = c;
                bestScore = score;
            }
        }
        return {x: best.x, y: best.y};
    }

    _toBackground(actor) {
        const bg = Main.layoutManager._backgroundGroup;
        if (actor.get_parent() !== bg) {
            console.log('[wpe-background] moving window actor to background group');
            actor.get_parent()?.remove_child(actor);
            bg.add_child(actor);
        }
        // Sit right above the shell's own background actors, not at the top of the group:
        // desktop widget extensions (e.g. Desktop Widgets/azclock) add their actors there too.
        const anchor = bg.get_children().filter(c => c instanceof Meta.BackgroundActor).at(-1) ?? null;
        if (!this._isAboveBackground(actor, anchor)) {
            if (anchor)
                bg.set_child_above_sibling(actor, anchor);
            else
                bg.set_child_at_index(actor, 0);
        }
        this._makeClickThrough(actor);
        actor.show();
    }

    // True when only other wallpaper windows sit between the actor and the anchor (one per monitor).
    _isAboveBackground(actor, anchor) {
        for (let c = actor.get_previous_sibling(); c !== anchor; c = c.get_previous_sibling()) {
            if (!c || !this._pinned.has(c))
                return false;
        }
        return true;
    }

    _makeClickThrough(actor) {
        const info = this._pinned.get(actor);
        if (!info)
            return;
        const visit = child => {
            if (info.input.has(child))
                return;
            const state = {reactive: child.reactive, signals: []};
            info.input.set(child, state);
            state.signals.push(
                child.connect('notify::reactive', () => {
                    if (child.reactive)
                        child.reactive = false;
                }),
                child.connect('child-added', (_parent, added) => visit(added)),
                child.connect('destroy', () => info.input.delete(child)),
            );
            // A non-reactive parent does not exclude its reactive children from
            // Clutter picking. MetaSurfaceActor still intercepts clicks unless
            // the entire window subtree is non-reactive.
            child.reactive = false;
            child.get_children().forEach(visit);
        };
        visit(actor);
    }

    // Mutter keeps normal windows out of the top bar's strut, which pushes the wallpaper 32px down.
    // The actor lives in the background group, so we can simply pin it to the target's corner.
    _place(actor) {
        const info = this._pinned.get(actor);
        if (!info)
            return;
        const {x, y} = info.target;
        if (actor.x !== x || actor.y !== y) {
            info.placing = true;
            actor.set_position(x, y);
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

        const target = this._targetFor(win);
        console.log(`[wpe-background] pinning "${win.get_title()}" at ${target.x},${target.y}`);
        win.stick();
        this._toBackground(actor);

        // A wallpaper must never stay minimized or hidden
        const reassign = () => {
            const info = this._pinned?.get(actor);
            if (!info || info.placing)
                return;
            const t = this._targetFor(win);
            if (t.x !== info.target.x || t.y !== info.target.y) {
                console.log(`[wpe-background] window target is now ${t.x},${t.y}`);
                info.target = t;
            }
            this._place(actor);
        };
        const winIds = [
            win.connect('size-changed', reassign),
            win.connect('position-changed', reassign),
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
        this._pinned.set(actor, {win: winIds, actor: actorIds, target, placing: false, input: new Map()});
        this._makeClickThrough(actor);
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
