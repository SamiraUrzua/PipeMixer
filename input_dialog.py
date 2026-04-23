from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QDialogButtonBox
)
from PySide6.QtCore import Qt
from models import Input


class InputDialog(QDialog):
    def __init__(self, available: list[Input], already_added: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Input")
        self.setMinimumWidth(400)
        self._selected: Input | None = None

        layout = QVBoxLayout(self)

        hardware = [i for i in available if i.media_class == "Audio/Source"]
        apps = [i for i in available if i.media_class == "Stream/Output/Audio"]

        if hardware:
            layout.addWidget(QLabel("Hardware Inputs"))
            self._hw_list = QListWidget()
            for inp in hardware:
                if inp.name not in already_added:
                    item = QListWidgetItem(inp.display_name or inp.name)
                    item.setData(Qt.UserRole, inp)
                    self._hw_list.addItem(item)
            self._hw_list.itemClicked.connect(self._on_select)
            layout.addWidget(self._hw_list)

        if apps:
            layout.addWidget(QLabel("App Inputs"))
            self._app_list = QListWidget()
            for inp in apps:
                if inp.name not in already_added:
                    item = QListWidgetItem(inp.display_name or inp.name)
                    item.setData(Qt.UserRole, inp)
                    self._app_list.addItem(item)
            self._app_list.itemClicked.connect(self._on_select)
            layout.addWidget(self._app_list)

        self._buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._buttons.button(QDialogButtonBox.Ok).setEnabled(False)
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

    def _on_select(self, item: QListWidgetItem):
        self._selected = item.data(Qt.UserRole)
        self._buttons.button(QDialogButtonBox.Ok).setEnabled(True)

    def selected_input(self) -> Input | None:
        return self._selected