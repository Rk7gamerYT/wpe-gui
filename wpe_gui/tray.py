"""System tray icon, like the Windows Wallpaper Engine: closing the window keeps the app (and the wallpapers) running.

On GNOME this needs the AppIndicator extension (enabled by default on Ubuntu); without a tray the window just closes
normally, so the app can never end up running with no way to reach it.
"""

import os
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, Qt, QTimer
from PySide6.QtGui import QAction, QIcon
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

ICONS = Path(__file__).parent / "assets/icons"
SERVER_NAME = f"wpe-gui-{os.getuid()}"


def app_icon() -> QIcon:
    icon = QIcon(str(ICONS / "app.svg"))
    for size in (32, 48, 64, 128, 256, 512):
        png = ICONS / "png" / f"app-{size}.png"
        if png.is_file():
            icon.addFile(str(png))
    return icon


def ask_running_instance_to_show() -> bool:
    """Used by a second launch: ask the app that is already running to bring its window up."""
    socket = QLocalSocket()
    socket.connectToServer(SERVER_NAME)
    if not socket.waitForConnected(500):
        return False
    socket.write(b"show\n")
    socket.waitForBytesWritten(500)
    socket.disconnectFromServer()
    return True


class Tray(QObject):
    def __init__(self, app, window, engine, settings, parent=None):
        super().__init__(parent)
        self._app = app
        self._window = window
        self._engine = engine
        self._settings = settings
        self._quitting = False

        self.icon = QSystemTrayIcon(app_icon(), self)
        self.icon.setToolTip("Wallpaper Engine")
        menu = QMenu()
        self._open = QAction("Abrir Wallpaper Engine", menu)
        self._open.triggered.connect(self.show_window)
        self._stop = QAction("Parar wallpapers", menu)
        self._stop.triggered.connect(engine.stop)
        quit_action = QAction("Sair", menu)
        quit_action.triggered.connect(self.quit)
        menu.addAction(self._open)
        menu.addAction(self._stop)
        menu.addSeparator()
        menu.addAction(quit_action)
        self._menu = menu  # keep a reference, the tray doesn't own it
        self.icon.setContextMenu(menu)
        self.icon.activated.connect(self._activated)
        engine.activeChanged.connect(lambda: self._stop.setEnabled(engine.running))
        self._stop.setEnabled(engine.running)

        window.installEventFilter(self)  # turn "close" into "hide to the tray"

        # A second launch of the app lands here and just shows the window
        QLocalServer.removeServer(SERVER_NAME)
        self._server = QLocalServer(self)
        self._server.newConnection.connect(self._on_connection)
        self._server.listen(SERVER_NAME)

        self.icon.show()

    @property
    def available(self) -> bool:
        return QSystemTrayIcon.isSystemTrayAvailable() and self.icon.isVisible()

    def _should_hide_on_close(self) -> bool:
        return bool(self._settings.get("closeToTray")) and not self._quitting and self.available

    def eventFilter(self, obj, event):
        if obj is self._window and event.type() == QEvent.Close:
            if self._should_hide_on_close():
                event.ignore()
                self._window.hide()
                return True
            if not self._quitting:
                # No tray to come back from: closing the window ends the app. Wait for the close to settle first,
                # the window may have refused it (e.g. a task still running).
                QTimer.singleShot(0, self._quit_if_closed)
        return False

    def _quit_if_closed(self):
        if not self._window.isVisible():
            self.quit()

    def show_window(self):
        self._window.show()
        self._window.setWindowState(Qt.WindowNoState if self._window.windowState() & Qt.WindowMinimized
                                    else self._window.windowState())
        self._window.raise_()
        self._window.requestActivate()

    def hide_window(self):
        self._window.hide()

    def _activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            if self._window.isVisible() and self._window.isActive():
                self.hide_window()
            else:
                self.show_window()

    def _on_connection(self):
        while self._server.hasPendingConnections():
            socket = self._server.nextPendingConnection()
            socket.readyRead.connect(lambda s=socket: (s.readAll(), self.show_window(), s.disconnectFromServer()))

    def quit(self):
        self._quitting = True
        self._app.quit()
