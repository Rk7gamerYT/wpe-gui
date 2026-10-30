"""Manual, asynchronous AppImage updates from this project's published GitHub releases."""
import hashlib
import os
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import urlparse

from PySide6.QtCore import QObject, Property, Signal, Slot, QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

from . import __version__

REPOSITORY = 'Rk7gamerYT/wpe-gui'
API_URL = f'https://api.github.com/repos/{REPOSITORY}/releases/latest'
RELEASE_URL = f'https://github.com/{REPOSITORY}/releases/latest'


def version_tuple(value):
    match = re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)', value)
    if not match:
        raise ValueError('Versão publicada inválida.')
    return tuple(map(int, match.groups()))


def select_update(release, current=__version__):
    if release.get('draft') or release.get('prerelease'):
        return None
    version = release.get('tag_name', '')
    if version_tuple(version) <= version_tuple(current):
        return None
    for asset in release.get('assets', []):
        if not asset.get('name', '').endswith('-x86_64.AppImage'):
            continue
        url = asset.get('browser_download_url', '')
        parsed = urlparse(url)
        if parsed.scheme != 'https' or parsed.hostname != 'github.com' or not parsed.path.startswith(f'/{REPOSITORY}/releases/download/'):
            raise ValueError('Endereço da atualização inválido.')
        digest = asset.get('digest', '') or ''
        if not re.fullmatch(r'sha256:[0-9a-f]{64}', digest):
            raise ValueError('A versão publicada não possui verificação SHA-256.')
        return {'version': version, 'url': url, 'sha256': digest[7:], 'size': int(asset.get('size', 0))}
    raise ValueError('A versão publicada ainda não possui um AppImage para este computador.')


def update_target():
    current = os.environ.get('APPIMAGE', '')
    if not current:
        raise ValueError('A atualização integrada instala o pacote AppImage. Baixe-o na página de versões.')
    target = Path(current).resolve()
    if target.is_file() and target.stat().st_uid == os.getuid() and os.access(target.parent, os.W_OK):
        return target
    data = Path(os.environ.get('XDG_DATA_HOME') or Path.home() / '.local/share')
    return data / 'wpe-gui/wpe-gui.AppImage'


def install_verified(download, target, expected):
    """Keep the old executable until a fully verified replacement is ready on the same filesystem."""
    digest = hashlib.sha256()
    with Path(download).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    if digest.hexdigest() != expected:
        raise ValueError('A verificação SHA-256 falhou. A versão atual foi preservada.')
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix='.wpe-update-', dir=target.parent)
    try:
        with os.fdopen(descriptor, 'wb') as output, Path(download).open('rb') as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b''):
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temporary, 0o755)
        os.replace(temporary, target)
    finally:
        Path(temporary).unlink(missing_ok=True)


class Updater(QObject):
    changed = Signal()
    restartRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._network = QNetworkAccessManager(self)
        self._busy = False
        self._status = ''
        self._update = None
        self._ready = ''
        self._progress = 0
        self._file = None
        self._temporary = None
        self._reply = None

    @Property(str, constant=True)
    def currentVersion(self):
        return __version__

    @Property(bool, constant=True)
    def packaged(self):
        return bool(os.environ.get('APPIMAGE'))

    @Property(bool, notify=changed)
    def busy(self):
        return self._busy

    @Property(str, notify=changed)
    def status(self):
        return self._status

    @Property(bool, notify=changed)
    def available(self):
        return self._update is not None

    @Property(bool, notify=changed)
    def ready(self):
        return bool(self._ready)

    @Property(float, notify=changed)
    def progress(self):
        return self._progress

    def _request(self, url):
        request = QNetworkRequest(QUrl(url))
        request.setRawHeader(b'User-Agent', b'wpe-gui-updater')
        request.setRawHeader(b'Accept', b'application/vnd.github+json')
        request.setTransferTimeout(60000)
        return request

    @Slot()
    def check(self):
        if self._busy:
            return
        self._busy, self._status = True, 'Verificando atualizações…'
        self.changed.emit()
        reply = self._network.get(self._request(API_URL))
        reply.finished.connect(lambda: self._checked(reply))

    def _checked(self, reply):
        import json
        self._busy = False
        try:
            if reply.error() != QNetworkReply.NoError:
                raise ValueError('Não foi possível consultar as versões publicadas. Tente novamente.')
            data = bytes(reply.readAll())
            if len(data) > 2_000_000:
                raise ValueError('Resposta de atualização inválida.')
            self._update = select_update(json.loads(data))
            self._status = f'Nova versão {self._update["version"]} disponível.' if self._update else 'Você está usando a versão mais recente.'
        except (ValueError, TypeError, KeyError) as error:
            self._update = None
            self._status = str(error)
        reply.deleteLater()
        self.changed.emit()

    @Slot()
    def download(self):
        if self._busy or not self._update:
            return
        try:
            update_target()
            descriptor, name = tempfile.mkstemp(prefix='wpe-update-', suffix='.AppImage')
            self._temporary = Path(name)
            self._file = os.fdopen(descriptor, 'wb')
        except (OSError, ValueError) as error:
            self._status = str(error)
            self.changed.emit()
            return
        self._busy, self._progress, self._status = True, 0, 'Baixando o pacote completo…'
        reply = self._network.get(self._request(self._update['url']))
        self._reply = reply
        reply.readyRead.connect(lambda: self._read(reply))
        reply.downloadProgress.connect(self._download_progress)
        reply.finished.connect(lambda: self._downloaded(reply))
        self.changed.emit()

    def _read(self, reply):
        if self._file:
            try:
                self._file.write(bytes(reply.readAll()))
            except OSError as error:
                self._status = str(error)
                reply.abort()

    def _download_progress(self, received, total):
        if received > 2_000_000_000:
            self._reply.abort()
        self._progress = received / total if total > 0 else 0
        self.changed.emit()

    def _downloaded(self, reply):
        self._read(reply)
        self._file.close()
        self._file = None
        try:
            if reply.error() != QNetworkReply.NoError:
                raise ValueError('Download interrompido. A versão atual foi preservada.')
            target = update_target()
            install_verified(self._temporary, target, self._update['sha256'])
            self._ready = str(target)
            self._status = 'Atualização instalada. Reinicie o app para usar a nova versão.'
        except (OSError, ValueError) as error:
            self._status = str(error)
        self._temporary.unlink(missing_ok=True)
        self._temporary = None
        self._busy = False
        self._reply = None
        reply.deleteLater()
        self.changed.emit()

    @Slot()
    def shutdown(self):
        if self._reply:
            self._reply.abort()

    @Slot()
    def openReleases(self):
        from PySide6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl(RELEASE_URL))

    @Slot()
    def restart(self):
        if not self._ready or self._busy:
            return
        # Wait outside the AppImage until Qt has stopped the engines and released its instance lock.
        environment = dict(os.environ)
        for key in ('APPIMAGE', 'APPDIR', 'PYTHONHOME', 'PYTHONPATH', 'QT_PLUGIN_PATH', 'QML2_IMPORT_PATH', 'WPE_BUNDLED_ENGINE'):
            environment.pop(key, None)
        subprocess.Popen(['/bin/sh', '-c', 'while kill -0 "$1" 2>/dev/null; do sleep 0.2; done; exec "$2"',
                          'wpe-restart', str(os.getpid()), self._ready], env=environment, start_new_session=True,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.restartRequested.emit()
