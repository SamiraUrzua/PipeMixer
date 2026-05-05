from PySide6.QtCore import Signal, Qt, QTimer, QEvent
from PySide6.QtGui import QIcon, QPainter, QFontMetrics
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QApplication,
    QSlider, QPushButton, QCheckBox, QFrame, QLineEdit, QSizePolicy
)
from models import Device, Input, Output, Link


class ElidingLabel(QLabel):
    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        self._full_text = text
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setMinimumWidth(0)

    def setText(self, text: str):
        self._full_text = text
        super().setText(text)
        self.update()

    def full_text(self) -> str:
        return self._full_text

    def paintEvent(self, event):
        painter = QPainter(self)
        fm = QFontMetrics(self.font())
        elided = fm.elidedText(self._full_text, Qt.ElideRight, self.width())
        style = self.style()
        opt = self.viewOptions() if hasattr(self, 'viewOptions') else None
        painter.setPen(self.palette().color(self.foregroundRole()))
        painter.drawText(self.rect(), self.alignment() or Qt.AlignLeft | Qt.AlignVCenter, elided)
        painter.end()


class RouteRow(QWidget):
    toggled = Signal(str, bool)
    removed = Signal(str)

    def __init__(self, input_name: str, display_name: str, connected: bool, available: bool, icon_name: str = "", parent=None):
        super().__init__(parent)
        self._input_name = input_name

        frame = QFrame(self)
        frame.setObjectName("route_row")
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 2, 0, 2)
        outer.addWidget(frame)

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(8, 4, 4, 4)

        if icon_name:
            icon = QIcon.fromTheme(icon_name)
            if not icon.isNull():
                icon_label = QLabel()
                icon_label.setPixmap(icon.pixmap(16, 16))
                icon_label.setFixedSize(16, 16)
                layout.addWidget(icon_label)

        self._label = QLabel(display_name)
        self._label.setObjectName("unavailable" if not available else "available")

        self._toggle = QPushButton("On" if connected else "Off")
        self._toggle.setObjectName("toggle_btn")
        self._toggle.setCheckable(True)
        self._toggle.setChecked(connected)
        self._toggle.setStyleSheet("""
            QPushButton { background:#45475a; color:#cdd6f4; border:none; border-radius:6px; padding:5px 8px; }
            QPushButton:checked { background:#89b4fa; color:#1e1e2e; border:none; }
            QPushButton:hover { background:#585b70; }
            QPushButton:checked:hover { background:#74c7ec; }
        """)
        self._toggle.toggled.connect(self._on_toggle)

        self._remove_btn = QPushButton("✕")
        self._remove_btn.setObjectName("remove_btn")
        self._remove_btn.setFixedSize(24, 24)
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

    def set_available(self, available: bool):
        self._label.setObjectName("unavailable" if not available else "available")
        self._label.setStyle(self._label.style())

    def set_display_name(self, name: str):
        self._label.setText(name)


class StreamRow(QWidget):
    toggled = Signal(str, bool)

    def __init__(self, stream_name: str, display_name: str, connected: bool, parent=None):
        super().__init__(parent)
        self._stream_name = stream_name

        frame = QFrame(self)
        frame.setObjectName("route_row")
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 2, 0, 2)
        outer.addWidget(frame)

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(8, 4, 4, 4)

        self._label = QLabel(display_name)

        self._toggle = QPushButton("On" if connected else "Off")
        self._toggle.setObjectName("toggle_btn")
        self._toggle.setCheckable(True)
        self._toggle.setChecked(connected)
        self._toggle.setStyleSheet("""
            QPushButton { background:#45475a; color:#cdd6f4; border:none; border-radius:6px; padding:5px 8px; }
            QPushButton:checked { background:#89b4fa; color:#1e1e2e; border:none; }
            QPushButton:hover { background:#585b70; }
            QPushButton:checked:hover { background:#74c7ec; }
        """)
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
    collapsed_toggled   = Signal(str, bool)
    rename_requested    = Signal(str, str)

    def __init__(self, device: Device, routes_expanded: bool = True, parent=None):
        super().__init__(parent)
        self._device         = device
        self._persisted_name = device.name
        self._dragging       = False
        self._cooling_down   = False
        self._pending_volume = device.volume
        self._is_output      = isinstance(device, Output)
        self._route_rows:    dict[str, RouteRow]  = {}
        self._stream_rows:   dict[str, StreamRow] = {}
        self._routes_expanded = routes_expanded

        self._volume_timer = QTimer()
        self._volume_timer.setSingleShot(True)
        self._volume_timer.setInterval(50)
        self._volume_timer.timeout.connect(self._emit_volume)

        self._build()

    def _build(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(4, 4, 4, 4)
        outer_layout.setSpacing(0)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        self._card = QFrame()
        self._card.setObjectName("card")
        outer_layout.addWidget(self._card)

        layout = QVBoxLayout(self._card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(8)

        self._icon_label = QLabel()
        self._icon_label.setFixedSize(20, 20)
        self._update_icon(getattr(self._device, 'icon_name', ''))
        header.addWidget(self._icon_label)

        display = getattr(self._device, 'display_name', '') or self._device.name
        self._label = ElidingLabel(display)
        self._label.mouseDoubleClickEvent = self._on_label_double_click

        self._rename_edit = QLineEdit()
        self._rename_edit.hide()
        self._rename_edit.returnPressed.connect(self._on_rename_confirm)
        self._rename_edit.editingFinished.connect(self._on_rename_confirm)

        self._remove_btn = QPushButton("✕")
        self._remove_btn.setObjectName("remove_btn")
        self._remove_btn.setFixedSize(24, 24)
        self._remove_btn.clicked.connect(lambda: self.remove_requested.emit(self._persisted_name))

        header.addWidget(self._label)
        header.addWidget(self._rename_edit)
        header.addWidget(self._remove_btn)
        layout.addLayout(header)

        slider_row = QHBoxLayout()
        slider_row.setSpacing(8)
        self._slider = QSlider(Qt.Horizontal)
        self._slider.setRange(0, 150)
        self._slider.setValue(int(self._device.volume * 100))
        self._slider.sliderPressed.connect(lambda: setattr(self, '_dragging', True))
        self._slider.sliderReleased.connect(lambda: setattr(self, '_dragging', False))
        self._slider.valueChanged.connect(self._on_volume)

        self._vol_label = QLabel(f"{int(self._device.volume * 100)}%")
        self._vol_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self._mute_btn = QPushButton("Mute")
        self._mute_btn.setObjectName("mute_btn")
        self._mute_btn.setCheckable(True)
        self._mute_btn.setChecked(self._device.muted)
        self._mute_btn.toggled.connect(self._on_mute)

        slider_row.addWidget(self._slider)
        slider_row.addWidget(self._vol_label)
        slider_row.addWidget(self._mute_btn)
        layout.addLayout(slider_row)

        if self._is_output:
            sep1 = QFrame()
            sep1.setObjectName("separator")
            sep1.setFrameShape(QFrame.HLine)
            layout.addWidget(sep1)

            routes_header = QHBoxLayout()
            routes_header.setSpacing(4)

            self._routes_collapse_btn = QPushButton("Sources")
            self._routes_collapse_btn.setObjectName("flat_btn")
            self._routes_collapse_btn.setFlat(True)
            self._routes_collapse_btn.clicked.connect(self._toggle_routes_collapsed)

            self._connect_source_btn = QPushButton("Connect source")
            self._connect_source_btn.setObjectName("add_btn")
            self._connect_source_btn.clicked.connect(
                lambda: self.route_add_requested.emit(self._persisted_name)
            )

            routes_header.addWidget(self._routes_collapse_btn)
            routes_header.addStretch()
            routes_header.addWidget(self._connect_source_btn)
            layout.addLayout(routes_header)

            self._routes_container = QWidget()
            self._routes_container.setStyleSheet("background: transparent;")
            self._routes_layout = QVBoxLayout(self._routes_container)
            self._routes_layout.setContentsMargins(0, 0, 0, 0)
            self._routes_layout.setSpacing(2)
            self._routes_container.setVisible(self._routes_expanded)
            layout.addWidget(self._routes_container)

            sep2 = QFrame()
            sep2.setObjectName("separator")
            sep2.setFrameShape(QFrame.HLine)
            layout.addWidget(sep2)

            auto_route_row = QHBoxLayout()
            self._auto_route = QCheckBox("Route all apps")
            self._auto_route.setChecked(self._device.auto_route)
            self._auto_route.toggled.connect(self._on_auto_route)
            auto_route_row.addWidget(self._auto_route)
            auto_route_row.addStretch()
            layout.addLayout(auto_route_row)

            self._streams_container = QWidget()
            self._streams_container.setStyleSheet("background: transparent;")
            self._streams_layout = QVBoxLayout(self._streams_container)
            self._streams_layout.setContentsMargins(0, 0, 0, 0)
            self._streams_layout.setSpacing(2)
            self._streams_container.setVisible(self._device.auto_route)
            layout.addWidget(self._streams_container)

            self._update_routes_header()

    def _toggle_routes_collapsed(self):
        if not self._route_rows:
            return
        self._routes_expanded = not self._routes_expanded
        self._routes_container.setVisible(self._routes_expanded)
        self._routes_container.updateGeometry()
        self._update_routes_header()
        self.collapsed_toggled.emit(self._persisted_name, self._routes_expanded)

    def _update_routes_header(self):
        count = len(self._route_rows)
        arrow = "▾" if self._routes_expanded else "▸"
        self._routes_collapse_btn.setText(f"{arrow} Sources ({count})")

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
        self._rename_edit.setText(self._label.full_text())
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

        self._full_display_name = new_name
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

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_label') and hasattr(self, '_full_display_name'):
            fm = self._label.fontMetrics()
            elided = fm.elidedText(self._full_display_name, Qt.ElideRight, self._label.width())
            self._label.setText(elided)

    def _update_icon(self, icon_name: str):
        if icon_name:
            icon = QIcon.fromTheme(icon_name)
            if not icon.isNull():
                self._icon_label.setPixmap(icon.pixmap(20, 20))
                return
        self._icon_label.clear()

    def set_available(self, available: bool):
        self._label.setObjectName("unavailable" if not available else "available")
        self._label.setStyle(self._label.style())
        self._slider.setEnabled(available)
        self._mute_btn.setEnabled(available)

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

    def add_route(self, input_name: str, display_name: str, connected: bool, available: bool = False, icon_name: str = ""):
        if input_name in self._route_rows:
            return
        row = RouteRow(input_name, display_name, connected, available, icon_name)
        row.toggled.connect(
            lambda name, state: self.route_toggled.emit(self._persisted_name, name, state)
        )
        row.removed.connect(
            lambda name: self.route_removed.emit(self._persisted_name, name)
        )
        self._routes_layout.addWidget(row)
        self._route_rows[input_name] = row
        if not self._routes_expanded:
            self._routes_expanded = True
        self._routes_container.setVisible(self._routes_expanded)
        self._routes_container.updateGeometry()
        self._update_routes_header()

    def remove_route(self, input_name: str):
        row = self._route_rows.pop(input_name, None)
        if row:
            row.setParent(None)
        if not self._route_rows:
            self._routes_expanded = False
            self._routes_container.setVisible(False)
        self._update_routes_header()

    def update_route_availability(self, input_name: str, available: bool):
        row = self._route_rows.get(input_name)
        if row:
            row.set_available(available)

    def update_route_display_name(self, input_name: str, display_name: str):
        row = self._route_rows.get(input_name)
        if row:
            row.set_display_name(display_name)

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