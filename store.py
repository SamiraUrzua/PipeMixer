import json
import os
from models import Input, Output, Link

STATE_PATH = os.path.expanduser("~/.config/pipemixer/state.json")


def save(inputs: list[Input], outputs: list[Output]) -> None:
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    data = {
        "inputs": [
            {
                "name": i.name,
                "binary": i.binary,
                "display_name": i.display_name,
                "volume": i.volume,
                "muted": i.muted,
            }
            for i in inputs
        ],
        "outputs": [
            {
                "name": o.name,
                "volume": o.volume,
                "muted": o.muted,
                "module_id": o.module_id,
                "auto_route": o.auto_route,
                "links": [
                    {"input_name": l.input_name, "volume": l.volume, "muted": l.muted}
                    for l in o.links
                ],
            }
            for o in outputs
        ],
    }
    with open(STATE_PATH, "w") as f:
        json.dump(data, f, indent=2)


def load() -> tuple[list[dict], list[dict]]:
    if not os.path.exists(STATE_PATH):
        return [], []
    try:
        with open(STATE_PATH) as f:
            data = json.load(f)
        return data.get("inputs", []), data.get("outputs", [])
    except Exception:
        return [], []