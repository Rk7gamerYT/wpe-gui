"""Qt model for the wallpaper grid, plus search/type filtering."""

from PySide6.QtCore import (
    QAbstractListModel, QModelIndex, QSortFilterProxyModel, Qt, QUrl, Property, Signal, Slot,
)

from . import library

ROLES = {
    Qt.UserRole + 1: b"wid",
    Qt.UserRole + 2: b"title",
    Qt.UserRole + 3: b"wtype",
    Qt.UserRole + 4: b"preview",
    Qt.UserRole + 5: b"path",
    Qt.UserRole + 6: b"description",
    Qt.UserRole + 7: b"tags",
}


class WallpaperModel(QAbstractListModel):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._items: list[library.Wallpaper] = []

    def roleNames(self):
        return ROLES

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._items)

    def data(self, index, role):
        w = self._items[index.row()]
        return {
            b"wid": w.id,
            b"title": w.title,
            b"wtype": w.type,
            b"preview": QUrl.fromLocalFile(str(w.preview)).toString() if w.preview else "",
            b"path": str(w.path),
            b"description": w.description,
            b"tags": ", ".join(w.tags),
        }.get(ROLES.get(role))

    @Slot(result="QVariant")
    def detectedDirs(self):
        return [str(d) for d in library.default_workshop_dirs()]

    @Slot(result=str)
    def detectedAssets(self):
        return str(library.default_assets_dir() or "")

    @Slot()
    def reload(self):
        from pathlib import Path
        dirs = library.default_workshop_dirs() + [Path(p) for p in self._settings.get("libraryDirs")]
        items = library.scan(dirs)
        self.beginResetModel()
        self._items = items
        self.endResetModel()


class WallpaperFilter(QSortFilterProxyModel):
    queryChanged = Signal()
    typeFilterChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._query = ""
        self._type = ""
        self.setSortRole(Qt.UserRole + 2)
        self.setSortCaseSensitivity(Qt.CaseInsensitive)
        self.sort(0)

    @Property(str, notify=queryChanged)
    def query(self):
        return self._query

    @query.setter
    def query(self, v):
        self._query = v.lower()
        self.invalidateFilter()
        self.queryChanged.emit()

    @Property(str, notify=typeFilterChanged)
    def typeFilter(self):
        return self._type

    @typeFilter.setter
    def typeFilter(self, v):
        self._type = v.lower()
        self.invalidateFilter()
        self.typeFilterChanged.emit()

    def filterAcceptsRow(self, row, parent):
        idx = self.sourceModel().index(row, 0, parent)
        title = idx.data(Qt.UserRole + 2).lower()
        tags = idx.data(Qt.UserRole + 7).lower()
        wtype = idx.data(Qt.UserRole + 3)
        if self._type and wtype != self._type:
            return False
        return self._query in title or self._query in tags
