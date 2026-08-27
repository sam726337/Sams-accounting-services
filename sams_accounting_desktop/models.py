from dataclasses import dataclass


@dataclass(frozen=True)
class Module:
    title: str
    subtitle: str
    metric: str
    state: str
    accent: str
    initials: str


@dataclass(frozen=True)
class Activity:
    time: str
    module: str
    description: str
    status: str
