from PySide6.QtCore import Signal, Qt, QTimer, QEvent
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QApplication,
    QSlider, QPushButton, QCheckBox, QFrame, QLineEdit
)
from models import Device, Input, Output, Link


class LinkRow(QWidget):
    volume_changed = Signal(str, float)
    mute_toggled = Signal(str, bool)

    def __init__(self, link: Link, parent=None):
        super().__init__(parent)
        self._link = link
        self._dragging = False
        self._pending_volume = link.volume

        self._volume_timer = QTimer()
        self._volume_timer.setSingleShot(True)
        self._volume_timer.setInterval(50)
        self._volume_timer.timeout.connect(self._emit_volume)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._label = QLabel(link.input_name)
        self._label.setFixedWidth(120)

        self._slider = QSlider(Qt.Horizontal)
        self._slider.setRange(0, 150)
        self._slider.setValue(int(link.volume * 100))
        self._slider.sliderPressed.connect(lambda: setattr(self, '_dragging', True))
        self._slider.sliderReleased.connect(lambda: setattr(self, '_dragging', False))
        self._slider.valueChanged.connect(self._on_volume)

        self._vol_label = QLabel(f"{int(link.volume * 100)}%")
        self._vol_label.setFixedWidth(36)

        self._mute_btn = QPushButton("M")
        self._mute_btn.setCheckable(True)
        self._mute_btn.setChecked(link.muted)
        self._mute_btn.setFixedWidth(28)
        self._mute_btn.toggled.connect(self._on_mute)

        layout.addWidget(self._label)
        layout.addWidget(self._slider)
        layout.addWidget(self._vol_label)
        layout.addWidget(self._mute_btn)

    def _on_volume(self, value: int):
        self._pending_volume = value / 100
        self._vol_label.setText(f"{value}%")
        self._volume_timer.start()

    def _emit_volume(self):
        self.volume_changed.emit(self._link.input_name, self._pending_volume)

    def _on_mute(self, muted: bool):
        self.mute_toggled.emit(self._link.input_name, muted)

    def refresh(self, link: Link):
        if self._dragging:
            return
        self._link = link
        self._slider.blockSignals(True)
        self._slider.setValue(int(link.volume * 100))
        self._slider.blockSignals(False)
        self._vol_label.setText(f"{int(link.volume * 100)}%")
        self._mute_btn.blockSignals(True)
        self._mute_btn.setChecked(link.muted)
        self._mute_btn.blockSignals(False)


class DeviceWidget(QWidget):
    volume_changed = Signal(int, float)
    mute_toggled = Signal(int, bool)
    auto_route_toggled = Signal(int, bool)
    link_volume_changed = Signal(int, str, float)
    link_mute_toggled = Signal(int, str, bool)
    remove_requested = Signal(str)
    rename_requested = Signal(str, str)

    def __init__(self, device: Device, parent=None):
        super().__init__(parent)
        self._device = device
        self._persisted_name = device.name
        self._dragging = False
        self._cooling_down = False
        self._pending_volume = device.volume
        self._is_output = isinstance(device, Output)
        self._link_rows: dict[str, LinkRow] = {}

        self._volume_timer = QTimer()
        self._volume_timer.setSingleShot(True)
        self._volume_timer.setInterval(50)
        self._volume_timer.timeout.connect(self._emit_volume)

        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)

        header = QHBoxLayout()

        display = getattr(self._device, 'display_name', '') or self._device.name
        self._label = QLabel(display)
        self._label.setAlignment(Qt.AlignLeft)
        self._label.mouseDoubleClickEvent = self._on_label_double_click

        self._rename_edit = QLineEdit()
        self._rename_edit.hide()
        self._rename_edit.returnPressed.connect(self._on_rename_confirm)
        self._rename_edit.editingFinished.connect(self._on_rename_confirm)

        self._remove_btn = QPushButton("✕")
        self._remove_btn.setFixedWidth(24)
        self._remove_btn.setFlat(True)
        self._remove_btn.clicked.connect(lambda: self.remove_requested.emit(self._persisted_name))

        header.addWidget(self._label)
        header.addWidget(self._rename_edit)
        header.addWidget(self._remove_btn)
        layout.addLayout(header)

        slider_row = QHBoxLayout()
        self._slider = QSlider(Qt.Horizontal)
        self._slider.setRange(0, 150)
        self._slider.setValue(int(self._device.volume * 100))
        self._slider.sliderPressed.connect(lambda: setattr(self, '_dragging', True))
        self._slider.sliderReleased.connect(lambda: setattr(self, '_dragging', False))
        self._slider.valueChanged.connect(self._on_volume)

        self._vol_label = QLabel(f"{int(self._device.volume * 100)}%")
        self._vol_label.setFixedWidth(36)

        self._mute_btn = QPushButton("Mute")
        self._mute_btn.setCheckable(True)
        self._mute_btn.setChecked(self._device.muted)
        self._mute_btn.setFixedWidth(48)
        self._mute_btn.toggled.connect(self._on_mute)

        slider_row.addWidget(self._slider)
        slider_row.addWidget(self._vol_label)
        slider_row.addWidget(self._mute_btn)
        layout.addLayout(slider_row)

        if self._is_output:
            separator = QFrame()
            separator.setFrameShape(QFrame.HLine)
            layout.addWidget(separator)

            self._auto_route = QCheckBox("All apps")
            self._auto_route.setChecked(self._device.auto_route)
            self._auto_route.toggled.connect(self._on_auto_route)
            layout.addWidget(self._auto_route)

            self._links_layout = QVBoxLayout()
            layout.addLayout(self._links_layout)
            self._rebuild_links()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress:
            if self._rename_edit.isVisible():
                if not self._rename_edit.geometry().contains(
                    self._rename_edit.mapFrom(self, event.globalPosition().toPoint() - self.pos())
                ):
                    self._on_rename_confirm()
                    QApplication.instance().removeEventFilter(self)
        return False

    def _on_label_double_click(self, event):
        self._label.hide()
        self._rename_edit.setText(self._label.text())
        self._rename_edit.show()
        self._rename_edit.setFocus()
        self._rename_edit.selectAll()
        QApplication.instance().installEventFilter(self)

    def _on_rename_confirm(self):
        if not self._rename_edit.isVisible():
            return

        QApplication.instance().removeEventFilter(self)

        new_name = self._rename_edit.text().strip()

        if not new_name:
            new_name = self._device.display_name or self._device.name

        self._label.setText(new_name)
        self.rename_requested.emit(self._persisted_name, new_name)

        self._rename_edit.hide()
        self._label.show()

    def _rebuild_links(self):
        while self._links_layout.count():
            item = self._links_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._link_rows.clear()

        for link in self._device.links:
            row = LinkRow(link)
            row.volume_changed.connect(
                lambda name, vol: self.link_volume_changed.emit(self._device.id, name, vol)
            )
            row.mute_toggled.connect(
                lambda name, muted: self.link_mute_toggled.emit(self._device.id, name, muted)
            )
            self._links_layout.addWidget(row)
            self._link_rows[link.input_name] = row

    def _on_volume(self, value: int):
        self._pending_volume = value / 100
        self._vol_label.setText(f"{value}%")
        self._volume_timer.start()

    def _emit_volume(self):
        if self._device.id == -1:
            return
        self._cooling_down = True
        self.volume_changed.emit(self._device.id, self._pending_volume)
        QTimer.singleShot(2000, lambda: setattr(self, '_cooling_down', False))

    def _on_mute(self, muted: bool):
        self.mute_toggled.emit(self._device.id, muted)

    def _on_auto_route(self, checked: bool):
        self.auto_route_toggled.emit(self._device.id, checked)

    def set_available(self, available: bool):
        color = "red" if not available else ""
        self._label.setStyleSheet(f"color: {color};")
        self._slider.setEnabled(available)
        self._mute_btn.setEnabled(available)

    def refresh(self, device: Device):
        if self._dragging or self._cooling_down:
            return
        self._device = device
        self._slider.blockSignals(True)
        self._slider.setValue(int(device.volume * 100))
        self._slider.blockSignals(False)
        self._vol_label.setText(f"{int(device.volume * 100)}%")
        self._mute_btn.blockSignals(True)
        self._mute_btn.setChecked(device.muted)
        self._mute_btn.blockSignals(False)

        if self._is_output:
            self._auto_route.blockSignals(True)
            self._auto_route.setChecked(device.auto_route)
            self._auto_route.blockSignals(False)
            self._rebuild_links()