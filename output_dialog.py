from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QDialogButtonBox, QLineEdit, QStackedWidget, QWidget
)
from PySide6.QtCore import Qt
from models import Output


class OutputDialog(QDialog):
    def __init__(self, available_hardware: list[Output], already_added: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Output")
        self.setMinimumWidth(440)
        self.setMinimumHeight(380)
        self._result_virtual_name: str | None = None
        self._result_hardware: Output | None = None

        layout = QVBoxLayout(self)

        type_row = QHBoxLayout()
        self._virtual_btn = QPushButton("Virtual Mic")
        self._virtual_btn.setCheckable(True)
        self._virtual_btn.setChecked(True)
        self._hardware_btn = QPushButton("Hardware")
        self._hardware_btn.setCheckable(True)
        self._virtual_btn.clicked.connect(lambda: self._switch(0))
        self._hardware_btn.clicked.connect(lambda: self._switch(1))
        type_row.addWidget(self._virtual_btn)
        type_row.addWidget(self._hardware_btn)
        layout.addLayout(type_row)

        self._stack = QStackedWidget()

        virtual_page = QWidget()
        virtual_layout = QVBoxLayout(virtual_page)
        virtual_layout.addWidget(QLabel("Mic name"))
        self._virtual_name_edit = QLineEdit("PipeMixer Mic")
        self._virtual_name_edit.selectAll()
        virtual_layout.addWidget(self._virtual_name_edit)
        self._stack.addWidget(virtual_page)

        hardware_page = QWidget()
        hardware_layout = QVBoxLayout(hardware_page)
        hardware_layout.addWidget(QLabel("Hardware Outputs"))
        self._hw_list = QListWidget()
        self._hw_list.setMinimumHeight(200)
        for out in available_hardware:
            if out.name not in already_added:
                item = QListWidgetItem(out.display_name or out.name)
                item.setData(Qt.UserRole, out)
                self._hw_list.addItem(item)
        self._hw_list.itemClicked.connect(self._on_hw_select)
        self._hw_list.itemDoubleClicked.connect(lambda item: (self._on_hw_select(item), self._on_accept()))
        hardware_layout.addWidget(self._hw_list)
        self._stack.addWidget(hardware_page)

        layout.addWidget(self._stack)

        self._buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._buttons.accepted.connect(self._on_accept)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

    def _switch(self, index: int):
        self._stack.setCurrentIndex(index)
        self._virtual_btn.setChecked(index == 0)
        self._hardware_btn.setChecked(index == 1)

    def _on_hw_select(self, item: QListWidgetItem):
        self._result_hardware = item.data(Qt.UserRole)

    def _on_accept(self):
        if self._stack.currentIndex() == 0:
            name = self._virtual_name_edit.text().strip()
            if name:
                self._result_virtual_name = name
                self.accept()
        else:
            if self._result_hardware is not None:
                self.accept()

    def result_virtual_name(self) -> str | None:
        return self._result_virtual_name

    def result_hardware(self) -> Output | None:
        return self._result_hardware