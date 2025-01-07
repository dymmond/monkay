import sys
from contextvars import ContextVar
from pathlib import Path
from threading import Lock

import pytest

from monkay import Cage, TransparentCage

target_ro = {"foo": "bar"}

target1_raw = {"foo": "bar"}
target2_raw = {1, 2, 4}
target1_caged: dict
Cage(
    globals(),
    {"caged": "monkey"},
    name="target1_caged",
    update_fn=lambda private, new: {**new, **private},
)
target2_caged: set = {500000, 600000}
Cage(globals(), {1, 2, 4}, name="target2_caged", update_fn=lambda private, new: private.union(new))

transparent_cage = TransparentCage(
    globals(), {1}, name="transparent_cage", skip_self_register=True
)


@pytest.fixture(autouse=True, scope="function")
def cleanup():
    for p in (Path(__file__).parent / "targets").iterdir():
        sys.modules.pop(f"tests.targets.{p.stem}", None)
    yield


def test_cages_overwrite():
    assert 500000 not in target2_caged
    assert 600000 not in target2_caged
    assert 1 in target2_caged


def test_cages_override():
    # for preventing linting issues
    target1_caged = globals()["target1_caged"]
    assert target1_caged == {"caged": "monkey"}

    with target1_caged.monkay_with_override({"caged": "lion"}):
        assert target1_caged == {"caged": "lion"}
        with target1_caged.monkay_with_override({"caged": "zebra"}, allow_value_update=False):
            assert target1_caged == {"caged": "zebra"}
            with target1_caged.monkay_with_original() as original:
                original["elephant"] = True
            assert target1_caged == {"caged": "zebra"}
        # should affect override
        assert target1_caged == {"caged": "lion", "elephant": True}
    # should affect the new version
    assert target1_caged == {"caged": "monkey", "elephant": True}


def test_cages_preload_and_register():
    d = {}
    assert "tests.targets.module_prefixed" not in sys.modules
    assert "tests.targets.cages_preloaded" not in sys.modules
    assert "tests.targets.cages_preloaded_fn" not in sys.modules
    cage = Cage(
        d,
        target_ro,
        name="target_ro",
        preloads=[
            "tests.targets.module_prefixed",
            "tests.targets.cages_preloaded:load",
        ],
    )
    assert "tests.targets.module_prefixed" in sys.modules
    assert "tests.targets.cages_preloaded" in sys.modules
    assert "tests.targets.cages_preloaded_fn" in sys.modules
    assert isinstance(d["target_ro"], Cage)
    assert d["target_ro"] is cage
    assert isinstance(d["_target_ro_ctx"], ContextVar)


def test_cages_fail_without_name():
    with pytest.raises(TypeError):
        Cage(
            {},
            target_ro,
        )


def test_cages_retrieve_with_name():
    Cage(
        globals(),
        name="target_ro",
        context_var_name="foo_cages_retrieve_with_name_ctx",
        skip_self_register=True,
    )
    assert type(globals()["target_ro"]) is not Cage
    assert isinstance(globals()["foo_cages_retrieve_with_name_ctx"], ContextVar)


def test_transparent_cage():
    assert transparent_cage.name == "transparent_cage"
    assert transparent_cage.get() == {1}
    assert transparent_cage == {1}
    token = transparent_cage.set({2})
    assert transparent_cage == {2}
    transparent_cage.reset(token)
    assert transparent_cage == {1}


@pytest.mark.parametrize("read_lock", [True, False])
def test_cages_wrapper_for_non_existing(read_lock):
    lock = Lock()

    def update_fn(context_content, original):
        assert lock.locked() == read_lock
        return original + context_content

    cage = Cage(
        globals(),
        [],
        name="target_cages_wrapper",
        context_var_name=f"foo_cages_wrapper_ctx{read_lock}",
        skip_self_register=True,
        original_wrapper=lock,
        use_wrapper_for_reads=read_lock,
        update_fn=update_fn,
    )
    assert type(globals()["target_ro"]) is not Cage
    assert isinstance(globals()[f"foo_cages_wrapper_ctx{read_lock}"], ContextVar)
    assert cage == []
    cage.append("b")
    assert cage == ["b"]

    with cage.monkay_with_original() as original:
        original.append("a")
    assert cage == ["a", "b"]
    cage.append("c")
    assert cage == ["a", "b", "c"]
