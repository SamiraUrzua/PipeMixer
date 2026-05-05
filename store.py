import json
import os

STATE_PATH = os.path.expanduser("~/.config/pipemixer/state.json")


def save(inputs: list[dict], outputs: list[dict]) -> None:
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w") as f:
        json.dump({"inputs": inputs, "outputs": outputs}, f, indent=2)


def load() -> tuple[list[dict], list[dict]]:
    if not os.path.exists(STATE_PATH):
        return [], []
    try:
        with open(STATE_PATH) as f:
            data = json.load(f)
        inputs  = [i for i in data.get("inputs", [])  if isinstance(i.get("name"), str)]
        outputs = [o for o in data.get("outputs", []) if isinstance(o.get("name"), str)]
        return inputs, outputs
    except Exception:
        return [], []


ICON_CACHE_PATH = os.path.expanduser("~/.config/pipemixer/icon_cache.json")


def save_icon(key: str, icon_name: str) -> None:
    cache = load_icon_cache()
    if cache.get(key) == icon_name:
        return
    cache[key] = icon_name
    os.makedirs(os.path.dirname(ICON_CACHE_PATH), exist_ok=True)
    with open(ICON_CACHE_PATH, "w") as f:
        json.dump(cache, f)


def load_icon_cache() -> dict[str, str]:
    if not os.path.exists(ICON_CACHE_PATH):
        return {}
    try:
        with open(ICON_CACHE_PATH) as f:
            return json.load(f)
    except Exception:
        return {}