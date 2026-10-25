"""Capture an active wallpaper and authenticate to install a static Ubuntu GDM background."""

import shutil
import tempfile
from pathlib import Path

from PySide6.QtCore import QObject, Property, QProcess, QTimer, Signal, Slot
from PySide6.QtGui import QImage

from .login_helper import PNG_END


class LoginBackground(QObject):
    changed = Signal()
    message = Signal(str)

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._busy = False
        self._temporary = None
        self._capture = None
        self._ticks = 0
        self._timer = QTimer(self, interval=500)
        self._timer.timeout.connect(self._check_capture)
        self._auth = QProcess(self)
        self._auth.setProcessChannelMode(QProcess.MergedChannels)
        self._auth.finished.connect(self._finished)
        self._auth.errorOccurred.connect(self._auth_error)

    @Property(bool, notify=changed)
    def busy(self):
        return self._busy

    @Property(bool, constant=True)
    def supported(self):
        schema = Path("/usr/share/glib-2.0/schemas/com.ubuntu.login-screen.gschema.xml")
        return bool(shutil.which("pkexec") and schema.is_file()
                    and Path("/usr/share/gdm/generate-config").is_file())

    def _set_busy(self, value):
        self._busy = value
        self.changed.emit()

    def _cleanup(self):
        self._timer.stop()
        if self._temporary:
            self._temporary.cleanup()
            self._temporary = None
        self._capture = None
        self._set_busy(False)

    @Slot(str)
    def apply(self, folder):
        if self.busy or not self.supported:
            return
        self._temporary = tempfile.TemporaryDirectory(prefix="wpe-login-")
        self._capture = Path(self._temporary.name) / "capture.png"
        self._set_busy(True)
        try:
            started = self._engine.captureWallpaper(folder, str(self._capture))
        except OSError as error:
            self.message.emit(f"Não foi possível preparar a captura: {error}")
            self._cleanup()
            return
        if not started:
            self._cleanup()
            return
        self._ticks = 0
        self.message.emit("Capturando o wallpaper. Em seguida será solicitada a senha de administrador.")
        self._timer.start()

    def _check_capture(self):
        self._ticks += 1
        try:
            with self._capture.open("rb") as stream:
                stream.seek(-len(PNG_END), 2)
                complete = stream.read() == PNG_END
        except (OSError, ValueError):
            complete = False
        if complete:
            image = QImage(str(self._capture))
            if not image.isNull():
                self._timer.stop()
                # Re-encode a fully decoded image before passing it to the privileged helper.
                clean = self._capture.with_name("login.png")
                if image.save(str(clean), "PNG"):
                    self._authorize(["--apply", str(clean)])
                    return
        if self._ticks >= 120:
            self.message.emit("Não foi possível capturar o wallpaper em 60 segundos. Confira se ele está carregando.")
            self._cleanup()

    @Slot()
    def reset(self):
        if self.busy or not self.supported:
            return
        self._set_busy(True)
        self._authorize(["--reset"])

    def _authorize(self, args):
        self._resetting = args == ["--reset"]
        helper = str(Path(__file__).with_name("login_helper.py").resolve())
        self._auth.start("pkexec", ["/usr/bin/python3", "-I", helper, *args])

    def _auth_error(self, error):
        if error == QProcess.FailedToStart:
            self.message.emit("Não foi possível abrir a autenticação de administrador.")
            self._cleanup()

    def _finished(self, code, status):
        output = bytes(self._auth.readAll()).decode(errors="replace").strip()
        if code == 0 and status == QProcess.NormalExit:
            self.message.emit("Fundo anterior do login restaurado." if self._resetting else
                              "Imagem aplicada à tela de login. Ela aparecerá no próximo login após ligar o PC.")
        elif code in (126, 127):
            self.message.emit("Autenticação cancelada ou não autorizada; o fundo do login não foi alterado.")
        else:
            self.message.emit(f"Não foi possível alterar o fundo do login. {output[-500:]}")
        self._cleanup()
