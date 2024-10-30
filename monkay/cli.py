from __future__ import annotations

from importlib import import_module
from typing import Any

import click


@click.group(name="cli")
def _cli() -> None:
    pass


def cli(*args: Any, **kwargs: Any) -> None:
    module = import_module("monkay.operations")
    for command in module.__all__:
        _cli.add_command(getattr(module, command))
    _cli(*args, **kwargs)
