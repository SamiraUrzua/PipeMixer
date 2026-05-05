from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QDialogButtonBox
)
from PySide6.QtCore import Qt
from models import Input


class InputDialog(QDialog):
    def __init__(self, available: list[Input], already_added: list[str], parent=None, title: str = "Add Source"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(440)
        self.setMinimumHeight(420)
        self._selected: Input | None = None
        self._lists: list[QListWidget] = []

        layout = QVBoxLayout(self)

        hardware = [i for i in available if i.media_class == "Audio/Source"]
        apps     = [i for i in available if i.media_class == "Stream/Output/Audio"]
        other    = [i for i in available if i.media_class not in ("Audio/Source", "Stream/Output/Audio")]

        def add_list(label: str, items: list[Input]):
            if not items:
                return
            filtered = [i for i in items if i.name not in already_added]
            if not filtered:
                return
            layout.addWidget(QLabel(label))
            lst = QListWidget()
            lst.setMinimumHeight(120)
            for inp in filtered:
                item = QListWidgetItem(inp.display_name or inp.name)
                item.setData(Qt.UserRole, inp)
                lst.addItem(item)
            lst.itemClicked.connect(lambda item, l=lst: self._on_select(item, l))
            lst.itemDoubleClicked.connect(lambda item, l=lst: self._on_double_click(item, l))
            layout.addWidget(lst)
            self._lists.append(lst)

        if hardware or apps:
            add_list("Hardware Sources", hardware)
            add_list("App Sources", apps)
        else:
            add_list("Sources", other)

        self._buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._buttons.button(QDialogButtonBox.Ok).setEnabled(False)
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

    def _on_select(self, item: QListWidgetItem, source_list: QListWidget):
        for lst in self._lists:
            if lst is not source_list:
                lst.clearSelection()
        self._selected = item.data(Qt.UserRole)
        self._buttons.button(QDialogButtonBox.Ok).setEnabled(True)

    def _on_double_click(self, item: QListWidgetItem, source_list: QListWidget):
        self._on_select(item, source_list)
        self.accept()

    def selected_input(self) -> Input | None:
        return self._selected