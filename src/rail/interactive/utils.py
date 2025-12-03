import functools
import sys
import types
from collections.abc import Callable
from typing import Any

import rail.stages
from rail.core import RailEnv
from rail.core.stage import RailStage

rail.stages.import_and_attach_all()

_stage_names = list(RailStage.pipeline_stages.keys())
_stage_names = [
    i
    for i in _stage_names
    if i not in RailEnv._base_stages_names  # pylint: disable=protected-access
]
_stage_names.sort()


def _interactive_factory(rail_stage: RailStage, **kwargs) -> Any:
    instance = rail_stage.make_stage(**kwargs)
    entrypoint_function_name = instance.entrypoint_function
    entrypoint_function: Callable = getattr(instance, entrypoint_function_name)
    return entrypoint_function(**kwargs)


def _get_all_stage_names() -> list[str]:
    return _stage_names


def _get_stage_definition(stage_name: str) -> type:
    return RailStage.pipeline_stages[stage_name][0]


def _get_stage_module(stage_name: str, interactive: bool = False) -> str:
    module = _get_stage_definition(stage_name).__module__
    if interactive:
        return module.replace("rail.", "rail.interactive.", count=1)
    return module


def _create_virtual_submodules(module: types.ModuleType, stage_names: list[str]):
    # note: should be made recursive
    stage_modules = [
        _get_stage_module(stage, interactive=True) for stage in stage_names
    ]
    stage_modules = list(set(stage_modules))

    for virtual_module_name in stage_modules:
        virtual_module = types.ModuleType(virtual_module_name, "docstring")
        module.__all__.append(virtual_module_name.split(".")[-1])
        sys.modules[virtual_module_name] = virtual_module
        setattr(
            module,
            virtual_module_name.split(".")[-1],
            virtual_module,
        )


def _attatch_interactive_function(stage_name: str) -> None:
    stage_definition = _get_stage_definition(stage_name)
    function_name = stage_definition.interactive_function
    created_function: Callable = functools.partial(
        _interactive_factory, stage_definition
    )
    virtual_module_name = _get_stage_module(stage_name, interactive=True)
    virtual_module = sys.modules[virtual_module_name]

    # how much of stub_string can come from inspect
    _ = f"def {function_name}(**kwargs:Any)"

    setattr(virtual_module, function_name, created_function)
