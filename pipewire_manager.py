import hashlib
import json
import os
import subprocess
import threading
import time

from PySide6.QtCore import QThread, Signal

from models import Input, Output, Link


IGNORED_MEDIA_CLASSES = {"Midi/Bridge", "Video/Source", "Video/Sink"}
IGNORED_NODE_NAMES    = {"Dummy-Driver", "Freewheel-Driver", "Midi-Bridge"}
IGNORED_CLIENT_NAMES  = {"WirePlumber", "pipewire", "speech-dispatcher-dummy"}

POLL_INTERVAL = 0.1


def _run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
    if result.returncode != 0:
        raise RuntimeError(f"{cmd} failed: {result.stderr.strip()}")
    return result.stdout


def _parse_dump(raw: str) -> list:
    arrays = []
    for part in raw.strip().split("\n["):
        text = part if part.startswith("[") else "[" + part
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                arrays.append(parsed)
        except json.JSONDecodeError:
            pass

    for candidate in reversed(arrays):
        objects = [o for o in candidate if isinstance(o, dict)]
        if any(o.get("type") == "PipeWire:Interface:Core" for o in objects):
            return objects

    return []


def _avg(channel_volumes: list[float]) -> float:
    if not channel_volumes:
        return 0.0
    linear = sum(channel_volumes) / len(channel_volumes)
    return round(linear ** (1 / 3), 4)


def _snapshot_hash(objects: list) -> str:
    entries = []
    for obj in objects:
        t = obj.get("type", "")
        if t == "PipeWire:Interface:Node":
            info        = obj.get("info", {})
            props       = info.get("props", {})
            media_class = props.get("media.class", "")
            if not (media_class.startswith("Audio/") or media_class.startswith("Stream/")):
                continue
            vp = info.get("params", {}).get("Props", [{}])[0]
            entries.append((
                "node", obj["id"], media_class,
                vp.get("mute"),
                tuple(vp.get("channelVolumes", []) or []),
            ))
        elif t == "PipeWire:Interface:Link":
            li = obj.get("info", {})
            entries.append((
                "link", obj["id"],
                li.get("output-node-id"),
                li.get("input-node-id"),
            ))
    return hashlib.md5(repr(tuple(entries)).encode()).hexdigest()


class PipewireManager:

    def __init__(self):
        self._lock    = threading.RLock()
        self._objects: list = []

    def _update(self, objects: list) -> None:
        with self._lock:
            self._objects = objects

    def _get_objects(self) -> list:
        with self._lock:
            return list(self._objects)

    def _client_info(self, objects: list) -> dict[int, dict]:
        info = {}
        for obj in objects:
            if obj.get("type") != "PipeWire:Interface:Client":
                continue
            props = obj.get("info", {}).get("props", {})
            info[obj["id"]] = {
                "name":   props.get("application.name", ""),
                "binary": props.get("application.process.binary", ""),
            }
        return info

    def discover_inputs(self) -> list[Input]:
        objects = self._get_objects()
        clients = self._client_info(objects)

        hardware: list[Input]      = []
        streams:  dict[str, Input] = {}

        for obj in objects:
            if obj.get("type") != "PipeWire:Interface:Node":
                continue

            props       = obj.get("info", {}).get("props", {})
            media_class = props.get("media.class", "")

            if media_class not in ("Audio/Source", "Stream/Output/Audio"):
                continue
            if props.get("node.name") in IGNORED_NODE_NAMES:
                continue
            if media_class in IGNORED_MEDIA_CLASSES:
                continue

            client_id   = props.get("client.id")
            client      = clients.get(client_id, {})
            client_name = client.get("name", "")
            binary      = client.get("binary", "")

            if client_name in IGNORED_CLIENT_NAMES:
                continue

            vol_props = obj.get("info", {}).get("params", {}).get("Props", [{}])[0]
            node_id   = obj["id"]
            node_name = props.get("node.name", "")

            if media_class == "Audio/Source":
                description = props.get("node.description", node_name)
                hardware.append(Input(
                    id=node_id,
                    name=node_name,
                    volume=_avg(vol_props.get("channelVolumes", [1.0])),
                    muted=vol_props.get("mute", False),
                    is_virtual=props.get("node.virtual", False),
                    media_class=media_class,
                    node_ids=[node_id],
                    binary="",
                    display_name=description,
                ))

            elif media_class == "Stream/Output/Audio":
                key = binary or client_name
                if key in streams:
                    streams[key].node_ids.append(node_id)
                else:
                    streams[key] = Input(
                        id=node_id,
                        binary=binary,
                        name=client_name,
                        display_name=f"{client_name} ({binary})",
                        volume=_avg(vol_props.get("channelVolumes", [1.0])),
                        muted=vol_props.get("mute", False),
                        is_virtual=props.get("node.virtual", False),
                        media_class=media_class,
                        node_ids=[node_id],
                    )

        return hardware + list(streams.values())

    def read_outputs(self) -> list[Output]:
        objects = self._get_objects()
        outputs = []

        for obj in objects:
            if obj.get("type") != "PipeWire:Interface:Node":
                continue

            props       = obj.get("info", {}).get("props", {})
            media_class = props.get("media.class", "")

            if media_class not in ("Audio/Sink", "Audio/Source/Virtual"):
                continue
            if props.get("node.name") in IGNORED_NODE_NAMES:
                continue

            vol_props = obj.get("info", {}).get("params", {}).get("Props", [{}])[0]

            node_name = props.get("node.name", "")
            description = props.get("node.description", node_name)

            outputs.append(Output(
                id=obj["id"],
                name=node_name,
                display_name=description,
                volume=_avg(vol_props.get("channelVolumes", [1.0])),
                muted=vol_props.get("mute", False),
                is_virtual=props.get("node.virtual", False),
            ))

        return outputs

    def set_volume(self, node_id: int, volume: float) -> None:
        volume = max(0.0, min(1.5, volume))
        _run(["wpctl", "set-volume", str(node_id), f"{volume:.4f}"])

    def set_mute(self, node_id: int, muted: bool) -> None:
        _run(["wpctl", "set-mute", str(node_id), "1" if muted else "0"])

    def set_input_volume(self, inp: Input, volume: float) -> None:
        for node_id in inp.node_ids:
            self.set_volume(node_id, volume)

    def set_input_mute(self, inp: Input, muted: bool) -> None:
        for node_id in inp.node_ids:
            self.set_mute(node_id, muted)

    def _write_virtual_mic_conf(self, node_name: str, display_name: str) -> None:
        conf_dir = os.path.expanduser("~/.config/pipewire/pipewire.conf.d")
        os.makedirs(conf_dir, exist_ok=True)
        conf_path = os.path.join(conf_dir, f"pipemixer-{node_name}.conf")
        with open(conf_path, "w") as f:
            f.write(
                f'context.objects = [\n'
                f'  {{\n'
                f'    factory = adapter\n'
                f'    args = {{\n'
                f'      factory.name     = support.null-audio-sink\n'
                f'      node.name        = {node_name}\n'
                f'      node.description = "{display_name}"\n'
                f'      media.class      = Audio/Source/Virtual\n'
                f'      object.linger    = true\n'
                f'    }}\n'
                f'  }}\n'
                f']\n'
            )

    def create_virtual_mic(self, display_name: str) -> str:
        base_name = "".join(c if c.isalnum() else "_" for c in display_name)
        existing = {
            obj.get("info", {}).get("props", {}).get("node.name")
            for obj in self._get_objects()
            if obj.get("type") == "PipeWire:Interface:Node"
        }
        node_name = base_name
        counter = 2
        while node_name in existing:
            node_name = f"{base_name}_{counter}"
            counter += 1
        self._write_virtual_mic_conf(node_name, display_name)
        _run([
            "pw-cli", "create-node", "adapter",
            f'{{ factory.name=support.null-audio-sink node.name={node_name} '
            f'node.description="{display_name}" media.class=Audio/Source/Virtual object.linger=true }}',
        ])
        return node_name

    def rename_virtual_mic(self, node_name: str, new_display_name: str) -> None:
        self.destroy_virtual_mic(node_name)
        self._write_virtual_mic_conf(node_name, new_display_name)
        _run([
            "pw-cli", "create-node", "adapter",
            f'{{ factory.name=support.null-audio-sink node.name={node_name} '
            f'node.description="{new_display_name}" media.class=Audio/Source/Virtual object.linger=true }}',
        ])

    def destroy_virtual_mic(self, node_name: str) -> None:
        conf_path = os.path.expanduser(
            f"~/.config/pipewire/pipewire.conf.d/pipemixer-{node_name}.conf"
        )
        if os.path.exists(conf_path):
            os.remove(conf_path)
        objects = self._get_objects()
        for obj in objects:
            if obj.get("type") != "PipeWire:Interface:Node":
                continue
            if obj.get("info", {}).get("props", {}).get("node.name") == node_name:
                try:
                    _run(["pw-cli", "destroy", str(obj["id"])])
                except RuntimeError:
                    pass
                break

    def link_nodes(self, output_node_name: str, input_node_name: str) -> None:
        _run(["pw-link", output_node_name, input_node_name])

    def unlink_nodes(self, output_node_name: str, input_node_name: str) -> None:
        _run(["pw-link", "-d", output_node_name, input_node_name])


class PWMonitor(QThread):

    graph_changed = Signal()

    def __init__(self, cache: PipewireManager, parent=None):
        super().__init__(parent)
        self._cache      = cache
        self._is_running = False
        self._last_hash  = ""

    def run(self):
        self._is_running = True

        while self._is_running:
            try:
                result = subprocess.run(
                    ["pw-dump"],
                    capture_output=True, text=True, timeout=5,
                )
                if result.returncode != 0:
                    print(f"[PWMonitor] pw-dump failed (code {result.returncode}): {result.stderr.strip()}", flush=True)
                else:
                    objects = _parse_dump(result.stdout)
                    if objects:
                        self._cache._update(objects)
                        h = _snapshot_hash(objects)
                        if h != self._last_hash:
                            self._last_hash = h
                            self.graph_changed.emit()

            except Exception as e:
                print(f"[PWMonitor] unexpected error: {e}", flush=True)

            time.sleep(POLL_INTERVAL)

    def stop(self):
        self._is_running = False
        self.wait()