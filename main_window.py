from pipewire_manager import PipewireManager
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QFrame
)
from PySide6.QtCore import Qt
from models import Input, Output
from device_widget import DeviceWidget
from input_dialog import InputDialog
import store


def get_widgets(layout: QVBoxLayout) -> list[DeviceWidget]:
    return [
        layout.itemAt(i).widget()
        for i in range(layout.count())
        if isinstance(layout.itemAt(i).widget(), DeviceWidget)
    ]


class MainWindow(QMainWindow):
    def __init__(self, cache: PipewireManager, monitor):
        super().__init__()
        self.setWindowTitle("PipeMixer")
        self.setMinimumSize(900, 600)

        self._pw = cache
        self._monitor = monitor

        self._input_widgets: dict[str, DeviceWidget] = {}
        self._output_widgets: dict[int, DeviceWidget] = {}

        saved_inputs, saved_outputs = store.load()
        self._persisted_inputs: list[dict] = saved_inputs

        self._build()
        self._build_input_widgets()

        self._monitor.graph_changed.connect(self._refresh)

    def _build(self):
        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QHBoxLayout(root)

        inputs_panel = QWidget()
        inputs_layout = QVBoxLayout(inputs_panel)
        inputs_layout.setAlignment(Qt.AlignTop)

        inputs_layout.addWidget(QLabel("Inputs"))

        self._inputs_container = QWidget()
        self._inputs_layout = QVBoxLayout(self._inputs_container)
        self._inputs_layout.setAlignment(Qt.AlignTop)

        add_input_btn = QPushButton("+ Add input")
        add_input_btn.clicked.connect(self._add_input)

        inputs_layout.addWidget(self._inputs_container)
        inputs_layout.addWidget(add_input_btn)

        outputs_panel = QWidget()
        outputs_layout = QVBoxLayout(outputs_panel)
        outputs_layout.setAlignment(Qt.AlignTop)

        outputs_layout.addWidget(QLabel("Outputs"))

        self._outputs_container = QWidget()
        self._outputs_layout = QVBoxLayout(self._outputs_container)
        self._outputs_layout.setAlignment(Qt.AlignTop)

        add_output_btn = QPushButton("+ Add virtual output")
        add_output_btn.clicked.connect(self._add_virtual_output)

        outputs_layout.addWidget(self._outputs_container)
        outputs_layout.addWidget(add_output_btn)

        root_layout.addWidget(inputs_panel)
        root_layout.addWidget(outputs_panel)

    def _build_input_widgets(self):
        for saved in self._persisted_inputs:
            self._create_input_widget(saved)

    def _create_input_widget(self, saved: dict):
        name = saved["name"]

        node = Input(
            id=-1,
            name=name,
            volume=saved.get("volume", 1.0),
            muted=saved.get("muted", False),
            is_virtual=False,
            media_class="",
            node_ids=[],
            binary=saved.get("binary", ""),
            display_name=saved.get("display_name", name),
        )

        widget = DeviceWidget(node)
        widget.volume_changed.connect(
            lambda nid, vol, i=node: self._pw.set_input_volume(i, vol)
        )
        widget.mute_toggled.connect(
            lambda nid, muted, i=node: self._pw.set_input_mute(i, muted)
        )
        widget.remove_requested.connect(self._remove_input)
        widget.rename_requested.connect(self._rename_input)

        self._inputs_layout.addWidget(widget)
        self._input_widgets[name] = widget
        widget.set_available(False)

    def _add_input(self):
        discovered = self._pw.discover_inputs()
        already_added = [p["name"] for p in self._persisted_inputs]

        dialog = InputDialog(discovered, already_added, self)
        if dialog.exec():
            selected = dialog.selected_input()
            if not selected:
                return

            saved = {
                "name": selected.name,
                "binary": selected.binary,
                "display_name": selected.display_name,
                "volume": selected.volume,
                "muted": selected.muted,
            }

            self._persisted_inputs.append(saved)
            self._create_input_widget(saved)
            self._sync_input_availability(self._pw.discover_inputs())

    def _remove_input(self, name: str):
        self._persisted_inputs = [
            p for p in self._persisted_inputs if p["name"] != name
        ]

        if name in self._input_widgets:
            self._input_widgets.pop(name).deleteLater()

        self._save()

    def _rename_input(self, internal_name: str, new_display_name: str):
        for p in self._persisted_inputs:
            if p["name"] == internal_name:
                p["display_name"] = new_display_name
                break
        self._save()

    def _sync_outputs(self, outputs: list[Output]):
        current_ids = {o.id for o in outputs}

        for node_id in set(self._output_widgets) - current_ids:
            self._output_widgets.pop(node_id).deleteLater()

        existing_names = {w._device.name for w in self._output_widgets.values()}

        for out in outputs:
            if out.id in self._output_widgets:
                self._output_widgets[out.id].refresh(out)
            elif out.name not in existing_names:
                widget = DeviceWidget(out)
                widget.volume_changed.connect(self._pw.set_volume)
                widget.mute_toggled.connect(self._pw.set_mute)
                widget.auto_route_toggled.connect(self._on_auto_route)
                widget.link_volume_changed.connect(self._on_link_volume)
                widget.link_mute_toggled.connect(self._on_link_mute)

                self._outputs_layout.addWidget(widget)
                self._output_widgets[out.id] = widget

    def _refresh(self):
        discovered = self._pw.discover_inputs()
        outputs = self._pw.read_outputs()

        self._sync_input_availability(discovered)
        self._sync_outputs(outputs)
        self._save()

    def _sync_input_availability(self, discovered: list[Input]):
        by_name = {i.name: i for i in discovered}
        by_binary = {i.binary: i for i in discovered if i.binary}

        for saved in self._persisted_inputs:
            name = saved["name"]
            binary = saved.get("binary", "")
            widget = self._input_widgets.get(name)
            if not widget:
                continue

            node = by_binary.get(binary) or by_name.get(name)

            if node:
                widget.volume_changed.disconnect()
                widget.mute_toggled.disconnect()

                widget.volume_changed.connect(
                    lambda nid, vol, i=node: self._pw.set_input_volume(i, vol)
                )
                widget.mute_toggled.connect(
                    lambda nid, muted, i=node: self._pw.set_input_mute(i, muted)
                )

                widget.refresh(node)
                widget.set_available(True)
            else:
                widget.set_available(False)

    def _save(self):
        inputs_to_save = [
            Input(
                id=-1,
                name=p["name"],
                volume=p.get("volume", 1.0),
                muted=p.get("muted", False),
                is_virtual=False,
                media_class="",
                node_ids=[],
                binary=p.get("binary", ""),
                display_name=p.get("display_name", p["name"]),
            )
            for p in self._persisted_inputs
        ]

        ordered_outputs = get_widgets(self._outputs_layout)

        store.save(inputs_to_save, [w._device for w in ordered_outputs])

    def _on_auto_route(self, output_id: int, enabled: bool):
        pass

    def _on_link_volume(self, output_id: int, input_name: str, volume: float):
        pass

    def _on_link_mute(self, output_id: int, input_name: str, muted: bool):
        pass

    def _add_virtual_output(self):
        pass

    def closeEvent(self, event):
        self._monitor.stop()
        event.accept()