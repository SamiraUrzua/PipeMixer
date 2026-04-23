# PipeMixer

PipeMixer is a PipeWire audio mixer for Linux.

## Features

- Input and output device management
- Volume control and mute
- Device renaming
- Persistence of configuration
- Live monitoring of PipeWire graph
- Input add/remove support

## Architecture

- Monitor thread polls PipeWire graph every 1.5s
- MainWindow updates UI based on graph changes
- User actions trigger PipeWire commands via PipewireManager

## Status

Core audio management is implemented.
Routing and virtual sink features are in development.

## Requirements

- Python 3.10+
- PySide6
- PipeWire tools (`wpctl`, `pw-dump`, `pw-link`, `pactl`)

## Run

```bash
python pipemixer/main.py