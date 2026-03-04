from __future__ import annotations

import asyncio

import pytest

from monkay import Cage


@pytest.mark.anyio
async def test_cage_context_overrides_are_task_local() -> None:
    globals_dict: dict = {}
    cage = Cage(globals_dict, ["global"], name="items", skip_self_register=True)
    seen: list[list[str]] = []

    async def worker(value: str) -> None:
        with cage.monkay_with_override([value], allow_value_update=False):
            await asyncio.sleep(0)
            seen.append(cage.monkay_get())

    await asyncio.gather(worker("one"), worker("two"))

    assert sorted(seen) == [["one"], ["two"]]
    assert cage.monkay_get() == ["global"]
