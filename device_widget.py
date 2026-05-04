from PySide6.QtCore import Signal, Qt, QTimer, QEvent
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QApplication,
    QSlider, QPushButton, QCheckBox, QFrame, QLineEdit
)
from models import Device, Input, Output, Link


class RouteRow(QWidget):
    toggled  = Signal(str, bool)
    removed  = Signal(str)

    def __init__(self, input_name: str, display_name: str, connected: bool, parent=None):
        super().__init__(parent)
        self._input_name = input_name

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._label = QLabel(display_name)

        self._toggle = QPushButton("On" if connected else "Off")
        self._toggle.setCheckable(True)
        self._toggle.setChecked(connected)
        self._toggle.setFixedWidth(36)
        self._toggle.toggled.connect(self._on_toggle)

        self._remove_btn = QPushButton("✕")
        self._remove_btn.setFixedWidth(24)
        self._remove_btn.setFlat(True)
        self._remove_btn.clicked.connect(lambda: self.removed.emit(self._input_name))

        layout.addWidget(self._label)
        layout.addStretch()
        layout.addWidget(self._toggle)
        layout.addWidget(self._remove_btn)

    def _on_toggle(self, checked: bool):
        self._toggle.setText("On" if checked else "Off")
        self.toggled.emit(self._input_name, checked)

    def set_connected(self, connected: bool):
        self._toggle.blockSignals(True)
        self._toggle.setChecked(connected)
        self._toggle.setText("On" if connected else "Off")
        self._toggle.blockSignals(False)


class StreamRow(QWidget):
    toggled = Signal(str, bool)

    def __init__(self, stream_name: str, display_name: str, connected: bool, parent=None):
        super().__init__(parent)
        self._stream_name = stream_name

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._label = QLabel(display_name)

        self._toggle = QPushButton("On" if connected else "Off")
        self._toggle.setCheckable(True)
        self._toggle.setChecked(connected)
        self._toggle.setFixedWidth(36)
        self._toggle.toggled.connect(self._on_toggle)

        layout.addWidget(self._label)
        layout.addStretch()
        layout.addWidget(self._toggle)

    def _on_toggle(self, checked: bool):
        self._toggle.setText("On" if checked else "Off")
        self.toggled.emit(self._stream_name, checked)

    def set_connected(self, connected: bool):
        self._toggle.blockSignals(True)
        self._toggle.setChecked(connected)
        self._toggle.setText("On" if connected else "Off")
        self._toggle.blockSignals(False)


class DeviceWidget(QWidget):
    volume_changed      = Signal(int, float)
    mute_toggled        = Signal(int, bool)
    auto_route_toggled  = Signal(int, bool)
    route_add_requested = Signal(str)
    route_toggled       = Signal(str, str, bool)
    route_removed       = Signal(str, str)
    stream_toggled      = Signal(str, str, bool)
    remove_requested    = Signal(str)
    rename_requested    = Signal(str, str)

    def __init__(self, device: Device, parent=None):
        super().__init__(parent)
        self._device        = device
        self._persisted_name = device.name
        self._dragging      = False
        self._cooling_down  = False
        self._pending_volume = device.volume
        self._is_output     = isinstance(device, Output)
        self._route_rows:   dict[str, RouteRow]  = {}
        self._stream_rows:  dict[str, StreamRow] = {}

        self._volume_timer = QTimer()
        self._volume_timer.setSingleShot(True)
        self._volume_timer.setInterval(50)
        self._volume_timer.timeout.connect(self._emit_volume)

        self._build()

    def _build(self):
        self.setAutoFillBackground(True)
        self.setStyleSheet("""
            DeviceWidget {
                border: 1px solid palette(mid);
                border-radius: 4px;
            }
        """)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        inner_widget = QWidget()
        inner_widget.setObjectName("card")
        inner_widget.setStyleSheet("""
            QWidget#card {
                border: 1px solid palette(mid);
                border-radius: 4px;
                background-color: palette(base);
            }
        """)
        layout = QVBoxLayout(inner_widget)
        layout.setAlignment(Qt.AlignTop)
        outer.addWidget(inner_widget)

        header = QHBoxLayout()

        self._icon_label = QLabel()
        self._icon_label.setFixedSize(20, 20)
        header.addWidget(self._icon_label)
        self._update_icon(getattr(self._device, 'icon_name', ''))

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
            sep1 = QFrame()
            sep1.setFrameShape(QFrame.HLine)
            layout.addWidget(sep1)

            self._routes_label = QLabel("Inputs")
            layout.addWidget(self._routes_label)

            self._routes_layout = QVBoxLayout()
            layout.addLayout(self._routes_layout)

            add_route_btn = QPushButton("+ Add route")
            add_route_btn.setFlat(True)
            add_route_btn.clicked.connect(
                lambda: self.route_add_requested.emit(self._persisted_name)
            )
            layout.addWidget(add_route_btn)

            sep2 = QFrame()
            sep2.setFrameShape(QFrame.HLine)
            layout.addWidget(sep2)

            self._auto_route = QCheckBox("Route all apps")
            self._auto_route.setChecked(self._device.auto_route)
            self._auto_route.toggled.connect(self._on_auto_route)
            layout.addWidget(self._auto_route)

            self._streams_container = QWidget()
            self._streams_layout = QVBoxLayout(self._streams_container)
            self._streams_layout.setContentsMargins(0, 0, 0, 0)
            self._streams_container.setVisible(self._device.auto_route)
            layout.addWidget(self._streams_container)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress:
            if self._rename_edit.isVisible():
                global_pos = event.globalPosition().toPoint()
                local_pos  = self._rename_edit.mapFromGlobal(global_pos)
                if not self._rename_edit.rect().contains(local_pos):
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

        self._rename_edit.hide()
        self._label.show()

        if not new_name:
            if self._is_output and self._device.is_virtual:
                return
            new_name = self._device.display_name or self._device.name

        self._label.setText(new_name)
        self.rename_requested.emit(self._persisted_name, new_name)

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
        self._streams_container.setVisible(checked)
        self.auto_route_toggled.emit(self._device.id, checked)

    def set_available(self, available: bool):
        color = "red" if not available else ""
        self._label.setStyleSheet(f"color: {color};")
        self._slider.setEnabled(available)
        self._mute_btn.setEnabled(available)

    def _update_icon(self, icon_name: str):
        if icon_name:
            icon = QIcon.fromTheme(icon_name)
            if not icon.isNull():
                self._icon_label.setPixmap(icon.pixmap(20, 20))
                return
        self._icon_label.clear()

    def refresh(self, device: Device):
        if self._dragging or self._cooling_down:
            return
        self._device = device
        self._update_icon(getattr(device, 'icon_name', ''))
        self._slider.blockSignals(True)
        self._slider.setValue(int(device.volume * 100))
        self._slider.blockSignals(False)
        self._vol_label.setText(f"{int(device.volume * 100)}%")
        self._mute_btn.blockSignals(True)
        self._mute_btn.setChecked(device.muted)
        self._mute_btn.blockSignals(False)

    def add_route(self, input_name: str, display_name: str, connected: bool):
        if input_name in self._route_rows:
            return
        row = RouteRow(input_name, display_name, connected)
        row.toggled.connect(
            lambda name, state: self.route_toggled.emit(self._persisted_name, name, state)
        )
        row.removed.connect(
            lambda name: self.route_removed.emit(self._persisted_name, name)
        )
        self._routes_layout.addWidget(row)
        self._route_rows[input_name] = row

    def remove_route(self, input_name: str):
        row = self._route_rows.pop(input_name, None)
        if row:
            row.setParent(None)

    def update_route_state(self, input_name: str, connected: bool):
        row = self._route_rows.get(input_name)
        if row:
            row.set_connected(connected)

    def update_streams(self, streams: list, stream_states: dict[str, bool]):
        for name in list(self._stream_rows):
            self._stream_rows.pop(name).setParent(None)

        for stream in streams:
            connected = stream_states.get(stream.name, True)
            row = StreamRow(stream.name, stream.display_name, connected)
            row.toggled.connect(
                lambda sname, state: self.stream_toggled.emit(self._persisted_name, sname, state)
            )
            self._streams_layout.addWidget(row)
            self._stream_rows[stream.name] = row