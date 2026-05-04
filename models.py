from dataclasses import dataclass, field


@dataclass
class Device:
    id: int
    name: str
    volume: float
    muted: bool
    is_virtual: bool


@dataclass
class Link:
    input_name: str
    connected: bool = True


@dataclass
class Input(Device):
    media_class: str = ""
    node_ids: list[int] = field(default_factory=list)
    binary: str = ""
    display_name: str = ""
    icon_name: str = ""


@dataclass
class Output(Device):
    routes: list[Link] = field(default_factory=list)
    module_id: int | None = None
    auto_route: bool = False
    display_name: str = ""
    icon_name: str = ""