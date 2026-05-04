from pipewire_manager import PipewireManager
import subprocess
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton
)
from PySide6.QtCore import Qt
from models import Input, Output, Link
from device_widget import DeviceWidget
from input_dialog import InputDialog
from output_dialog import OutputDialog
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

        self._input_widgets:  dict[str, DeviceWidget] = {}
        self._output_widgets: dict[str, DeviceWidget] = {}

        self._owned_links: set[tuple[str, str]] = set()

        saved_inputs, saved_outputs = store.load()
        self._persisted_inputs:  list[dict] = saved_inputs
        self._persisted_outputs: list[dict] = saved_outputs

        self._build()
        self._build_input_widgets()
        self._build_output_widgets()

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
        self._inputs_layout.setSpacing(8)
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
        self._outputs_layout.setSpacing(8)
        add_output_btn = QPushButton("+ Add output")
        add_output_btn.clicked.connect(self._add_output)
        outputs_layout.addWidget(self._outputs_container)
        outputs_layout.addWidget(add_output_btn)

        root_layout.addWidget(inputs_panel)
        root_layout.addWidget(outputs_panel)

        restart_btn = QPushButton("Restart PipeWire")
        restart_btn.clicked.connect(self._restart_pipewire)
        root_layout.addWidget(restart_btn, alignment=Qt.AlignTop)

    def _build_input_widgets(self):
        for saved in self._persisted_inputs:
            self._create_input_widget(saved)

    def _build_output_widgets(self):
        for saved in self._persisted_outputs:
            self._create_output_widget(saved)

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

    def _create_output_widget(self, saved: dict):
        name = saved["name"]
        node = Output(
            id=-1,
            name=name,
            display_name=saved.get("display_name", name),
            volume=saved.get("volume", 1.0),
            muted=saved.get("muted", False),
            is_virtual=saved.get("is_virtual", False),
            module_id=saved.get("module_id"),
            auto_route=saved.get("auto_route", False),
        )
        widget = DeviceWidget(node)
        widget.volume_changed.connect(self._pw.set_volume)
        widget.mute_toggled.connect(self._pw.set_mute)
        widget.auto_route_toggled.connect(self._on_auto_route)
        widget.route_add_requested.connect(self._on_route_add_requested)
        widget.route_toggled.connect(self._on_route_toggled)
        widget.route_removed.connect(self._on_route_removed)
        widget.stream_toggled.connect(self._on_stream_toggled)
        widget.remove_requested.connect(self._remove_output)
        widget.rename_requested.connect(self._rename_output)
        self._outputs_layout.addWidget(widget)
        self._output_widgets[name] = widget
        widget.set_available(False)

        for route in saved.get("routes", []):
            input_name   = route["input_name"]
            connected    = route.get("connected", True)
            display_name = self._input_display_name(input_name)
            widget.add_route(input_name, display_name, connected=connected)

    def _input_display_name(self, input_name: str) -> str:
        for p in self._persisted_inputs:
            if p["name"] == input_name:
                return p.get("display_name", input_name)
        return input_name

    def _input_node_ids(self, input_name: str) -> list[int]:
        for p in self._persisted_inputs:
            if p["name"] != input_name:
                continue
            widget = self._input_widgets.get(input_name)
            if widget:
                return widget._device.node_ids
        return []

    def _output_node_name(self, output_name: str) -> str:
        return output_name

    def _refresh(self):
        discovered = self._pw.discover_inputs()
        outputs    = self._pw.read_outputs()
        live_links = self._pw.read_links()
        streams    = self._pw.discover_streams()

        self._sync_input_availability(discovered)
        self._sync_output_availability(outputs)
        self._sync_routes(live_links)
        self._sync_streams(streams)
        self._save()

    def _sync_input_availability(self, discovered: list[Input]):
        by_name   = {i.name: i for i in discovered}
        by_binary = {i.binary: i for i in discovered if i.binary}

        for saved in self._persisted_inputs:
            name   = saved["name"]
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

    def _sync_output_availability(self, outputs: list[Output]):
        by_name = {o.name: o for o in outputs}

        for saved in self._persisted_outputs:
            name   = saved["name"]
            widget = self._output_widgets.get(name)
            if not widget:
                continue

            node = by_name.get(name)

            if node:
                widget.volume_changed.disconnect()
                widget.mute_toggled.disconnect()
                widget.volume_changed.connect(self._pw.set_volume)
                widget.mute_toggled.connect(self._pw.set_mute)
                widget.refresh(node)
                widget.set_available(True)
            else:
                widget.set_available(False)

    def _sync_routes(self, live_links: dict[tuple[int, int], int]):
        for saved_out in self._persisted_outputs:
            output_name   = saved_out["name"]
            output_widget = self._output_widgets.get(output_name)
            if not output_widget:
                continue

            output_node_id = output_widget._device.id
            if output_node_id == -1:
                continue

            for route in saved_out.get("routes", []):
                input_name     = route["input_name"]
                should_connect = route.get("connected", True)
                input_widget   = self._input_widgets.get(input_name)
                if not input_widget:
                    continue

                for nid in input_widget._device.node_ids:
                    link_id = live_links.get((nid, output_node_id))
                    input_node_name = next(
                        (
                            obj.get("info", {}).get("props", {}).get("node.name", "")
                            for obj in self._pw._get_objects()
                            if obj.get("type") == "PipeWire:Interface:Node"
                            and obj.get("id") == nid
                        ),
                        None
                    )
                    if not input_node_name:
                        continue
                    if should_connect:
                        if link_id is not None:
                            try:
                                self._pw.set_link_passive(link_id, False)
                            except RuntimeError:
                                pass
                        else:
                            try:
                                self._pw.connect_nodes(input_node_name, nid, output_name, output_node_id)
                            except RuntimeError:
                                pass
                    else:
                        if link_id is not None:
                            try:
                                self._pw.disconnect_nodes(input_node_name, output_name)
                            except RuntimeError:
                                pass

    def _sync_streams(self, streams: list[Input]):
        live_links = self._pw.read_links()

        for saved_out in self._persisted_outputs:
            output_name   = saved_out["name"]
            output_widget = self._output_widgets.get(output_name)
            if not output_widget:
                continue

            if not saved_out.get("auto_route"):
                output_widget.update_streams([], {})
                continue

            output_node_id = output_widget._device.id
            if output_node_id == -1:
                continue

            stream_states = saved_out.setdefault("stream_states", {})

            for stream in streams:
                should_connect    = stream_states.get(stream.name, True)
                already_connected = any(
                    (nid, output_node_id) in live_links for nid in stream.node_ids
                )
                try:
                    self._pw.set_node_target(stream.id, "-1")
                except RuntimeError:
                    pass
                if should_connect and not already_connected:
                    try:
                        self._pw.connect_nodes(stream.name, stream.id, output_name, output_node_id)
                    except RuntimeError:
                        pass
                elif not should_connect and already_connected:
                    try:
                        self._pw.disconnect_nodes(stream.name, output_name)
                    except RuntimeError:
                        pass

            output_widget.update_streams(streams, stream_states)

    def _on_route_add_requested(self, output_name: str):
        already_routed = [
            r["input_name"]
            for p in self._persisted_outputs
            if p["name"] == output_name
            for r in p.get("routes", [])
        ]
        dialog = InputDialog(
            self._pw.discover_inputs(), already_routed, self
        )
        if not dialog.exec():
            return
        selected = dialog.selected_input()
        if not selected:
            return

        for p in self._persisted_outputs:
            if p["name"] == output_name:
                live_links     = self._pw.read_links()
                output_node_id = self._output_widgets[output_name]._device.id
                connected = any(
                    (inp_id, output_node_id) in live_links
                    for inp_id in selected.node_ids
                ) if output_node_id != -1 else False
                p.setdefault("routes", []).append({
                    "input_name": selected.name,
                    "connected":  connected,
                })
                break

        output_widget = self._output_widgets.get(output_name)
        if output_widget:
            display_name = self._input_display_name(selected.name)
            output_widget.add_route(selected.name, display_name, connected=connected)

        self._save()

    def _on_route_toggled(self, output_name: str, input_name: str, connect: bool):
        for p in self._persisted_outputs:
            if p["name"] == output_name:
                for r in p.get("routes", []):
                    if r["input_name"] == input_name:
                        r["connected"] = connect
                        break
                break

        output_widget = self._output_widgets.get(output_name)
        input_widget  = self._input_widgets.get(input_name)

        if not output_widget or not input_widget:
            self._save()
            return

        output_node_id = output_widget._device.id
        input_node_ids = input_widget._device.node_ids
        live_links     = self._pw.read_links()

        for inp_id in input_node_ids:
            link_id = live_links.get((inp_id, output_node_id))
            input_node_name = next(
                (
                    obj.get("info", {}).get("props", {}).get("node.name", "")
                    for obj in self._pw._get_objects()
                    if obj.get("type") == "PipeWire:Interface:Node"
                    and obj.get("id") == inp_id
                ),
                None
            )
            if not input_node_name:
                continue
            if connect:
                if link_id is not None:
                    try:
                        self._pw.set_link_passive(link_id, False)
                    except RuntimeError:
                        pass
                else:
                    try:
                        self._pw.connect_nodes(input_node_name, inp_id, output_name, output_node_id)
                    except RuntimeError:
                        pass
            else:
                if link_id is not None:
                    try:
                        self._pw.disconnect_nodes(input_node_name, output_name)
                    except RuntimeError:
                        pass

        self._save()

    def _on_route_removed(self, output_name: str, input_name: str):
        for p in self._persisted_outputs:
            if p["name"] == output_name:
                p["routes"] = [r for r in p.get("routes", []) if r["input_name"] != input_name]
                break

        output_widget = self._output_widgets.get(output_name)
        if output_widget:
            output_widget.remove_route(input_name)

        self._save()

    def _on_stream_toggled(self, output_name: str, stream_name: str, connect: bool):
        for p in self._persisted_outputs:
            if p["name"] == output_name:
                p.setdefault("stream_states", {})[stream_name] = connect
                break

        output_widget = self._output_widgets.get(output_name)
        if not output_widget:
            return

        output_node_id = output_widget._device.id
        live_links     = self._pw.read_links()
        streams        = self._pw.discover_streams()
        stream         = next((s for s in streams if s.name == stream_name), None)
        if stream is None:
            return

        for nid in stream.node_ids:
            link_id = live_links.get((nid, output_node_id))
            if link_id is not None:
                try:
                    self._pw.set_link_passive(link_id, not connect)
                except RuntimeError:
                    pass
            elif connect:
                try:
                    self._pw.connect_nodes(stream_name, stream.id, output_name, output_node_id)
                except RuntimeError:
                    pass

        self._save()

    def _on_auto_route(self, output_id: int, enabled: bool):
        for p in self._persisted_outputs:
            widget = self._output_widgets.get(p["name"])
            if not widget or widget._device.id != output_id:
                continue
            p["auto_route"] = enabled
            if enabled:
                streams = self._pw.discover_streams()
                self._sync_streams(streams)
            else:
                output_node_id = widget._device.id
                live_links     = self._pw.read_links()
                streams        = self._pw.discover_streams()
                manually_on    = {r["input_name"] for r in p.get("routes", [])}
                for stream in streams:
                    try:
                        self._pw.set_node_target(stream.id, "")
                    except RuntimeError:
                        pass
                    if stream.name in manually_on:
                        continue
                    for nid in stream.node_ids:
                        link_id = live_links.get((nid, output_node_id))
                        if link_id is not None:
                            try:
                                self._pw.disconnect_nodes(stream.name, p["name"])
                            except RuntimeError:
                                pass
                widget.update_streams([], {})
            break
        self._save()

    def _add_input(self):
        discovered    = self._pw.discover_inputs()
        already_added = [p["name"] for p in self._persisted_inputs]
        dialog = InputDialog(discovered, already_added, self)
        if not dialog.exec():
            return
        selected = dialog.selected_input()
        if not selected:
            return
        saved = {
            "name":         selected.name,
            "binary":       selected.binary,
            "display_name": selected.display_name,
            "volume":       selected.volume,
            "muted":        selected.muted,
        }
        self._persisted_inputs.append(saved)
        self._create_input_widget(saved)
        self._sync_input_availability(self._pw.discover_inputs())

    def _add_output(self):
        discovered    = self._pw.read_outputs()
        already_added = [p["name"] for p in self._persisted_outputs]
        dialog = OutputDialog(discovered, already_added, self)
        if not dialog.exec():
            return

        if dialog.result_virtual_name() is not None:
            display_name = dialog.result_virtual_name()
            try:
                node_name = self._pw.create_virtual_mic(display_name)
            except RuntimeError:
                return
            saved = {
                "name":         node_name,
                "display_name": display_name,
                "volume":       1.0,
                "muted":        False,
                "is_virtual":   True,
                "module_id":    None,
                "auto_route":   False,
                "routes":       [],
            }
            self._persisted_outputs.append(saved)
            self._create_output_widget(saved)
            self._output_widgets[node_name].set_available(True)

        elif dialog.result_hardware() is not None:
            out = dialog.result_hardware()
            saved = {
                "name":         out.name,
                "display_name": out.display_name,
                "volume":       out.volume,
                "muted":        out.muted,
                "is_virtual":   False,
                "module_id":    None,
                "auto_route":   False,
                "routes":       [],
            }
            self._persisted_outputs.append(saved)
            self._create_output_widget(saved)
            self._sync_output_availability(self._pw.read_outputs())

        self._save()

    def _remove_input(self, name: str):
        self._persisted_inputs = [
            p for p in self._persisted_inputs if p["name"] != name
        ]
        if name in self._input_widgets:
            self._input_widgets.pop(name).deleteLater()
        self._save()

    def _remove_output(self, name: str):
        saved = next((p for p in self._persisted_outputs if p["name"] == name), None)
        if saved and saved.get("is_virtual"):
            try:
                self._pw.destroy_virtual_mic(name)
            except RuntimeError:
                pass
        self._persisted_outputs = [
            p for p in self._persisted_outputs if p["name"] != name
        ]
        if name in self._output_widgets:
            self._output_widgets.pop(name).deleteLater()
        self._save()

    def _rename_input(self, internal_name: str, new_display_name: str):
        for p in self._persisted_inputs:
            if p["name"] == internal_name:
                p["display_name"] = new_display_name
                break
        self._save()

    def _rename_output(self, internal_name: str, new_display_name: str):
        for p in self._persisted_outputs:
            if p["name"] == internal_name:
                if p.get("is_virtual") and new_display_name != p.get("display_name"):
                    try:
                        self._pw.rename_virtual_mic(internal_name, new_display_name)
                    except RuntimeError:
                        pass
                p["display_name"] = new_display_name
                break
        self._save()

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
        outputs_to_save = [
            Output(
                id=-1,
                name=p["name"],
                display_name=p.get("display_name", p["name"]),
                volume=p.get("volume", 1.0),
                muted=p.get("muted", False),
                is_virtual=p.get("is_virtual", False),
                module_id=p.get("module_id"),
                auto_route=p.get("auto_route", False),
                routes=[
                    Link(input_name=r["input_name"])
                    for r in p.get("routes", [])
                ],
            )
            for p in self._persisted_outputs
        ]
        store.save(inputs_to_save, outputs_to_save)

    def _restart_pipewire(self):
        subprocess.run(["systemctl", "--user", "restart", "pipewire"], timeout=5)

    def closeEvent(self, event):
        self._monitor.stop()
        event.accept()