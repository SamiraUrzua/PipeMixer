# PipeMixer

PipeMixer is a PipeWire audio mixer for Linux. It lets you route audio sources to outputs, create virtual microphones, and control volumes — all without interfering with your normal system audio setup. Open it when you need it, close it when you don't.

## Features

- **Source management** — add hardware inputs and app streams as sources with volume and mute control
- **Output management** — add hardware outputs or create virtual microphones (appear as mic inputs in Discord, OBS, etc.)
- **Manual routing** — connect any source to any output with per-route on/off toggle
- **Route all apps** — automatically connect all currently playing app streams to an output
- **Virtual microphones** — persistent across reboots, survive PipeWire restarts, name changes reflected system-wide
- **Device renaming** — custom display names for all sources and outputs
- **Live pipewire monitoring** — reflects external changes in real time
- **Persistence** — sources, outputs, routes state saved across restarts
- **Dark theme** — clean dark UI with scrollable panels, collapsible route sections, and system icon support

## Architecture

| File | Responsibility |
|---|---|
| `pipewire_manager.py` | `PipewireManager` (data cache + control) and `PWMonitor` (poll thread). Single `pw-dump` every 100ms, all other code reads from cache. |
| `main_window.py` | Two-panel UI (Sources / Outputs), wires all signals, owns persisted state |
| `device_widget.py` | Card widget for both sources and outputs, includes route rows and stream rows |
| `input_dialog.py` | Dialog to add a source (hardware or app) |
| `output_dialog.py` | Dialog to add an output (virtual mic or hardware) |
| `store.py` | Saves/loads state to `~/.config/pipemixer/state.json`, icon cache to `~/.config/pipemixer/icon_cache.json` |
| `models.py` | `Device`, `Input`, `Output`, `Link` dataclasses |
| `theme.py` | Dark theme stylesheet applied at startup |
| `main.py` | Entry point |

## Requirements

- Python 3.10+
- PySide6
- PipeWire tools: `pw-dump`, `pw-link`, `pw-cli`, `pw-metadata`, `wpctl`

## Run

```bash
python main.py
```

## Notes

- Virtual microphones are created as `Audio/Source/Virtual` nodes via `pw-cli` and persisted via `~/.config/pipewire/pipewire.conf.d/`. They survive PipeWire restarts and will not disappear unless deleted from PipeMixer.
- Closing PipeMixer does not affect any existing audio connections or virtual devices.
- Route on/off state is owned entirely by PipeMixer — external changes from other apps (e.g. WirePlumber reconnecting the default device) are enforced against on the next poll cycle.