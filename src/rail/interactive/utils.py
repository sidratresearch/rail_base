import functools
import inspect
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
    # note: should be made recursive, stubs will need to be handled as well
    stage_modules = [
        _get_stage_module(stage, interactive=True) for stage in stage_names
    ]
    stage_modules = list(set(stage_modules))

    print("\n", module.__path__[0].strip() + "/__init__.pyi")
    for virtual_module_name in stage_modules:
        virtual_module = types.ModuleType(virtual_module_name, "docstring")
        sys.modules[virtual_module_name] = (
            virtual_module  # only needed because this is how we access it when attatching the function
        )
        setattr(
            module,
            virtual_module_name.split(".")[-1],
            virtual_module,
        )
        print(f"from . import {virtual_module_name.split('.')[-1]}")
    print()


def _attatch_interactive_function(stage_name: str) -> None:
    stage_definition = _get_stage_definition(stage_name)
    function_name = stage_definition.interactive_function
    created_function: Callable = functools.partial(
        _interactive_factory, stage_definition
    )
    created_function.__doc__ = """docstring

    Second summary

    Parameters
    ----------
    p1 : int
        about p1

    Returns
    -------
    float
        It returns a float
    """

    virtual_module_name = _get_stage_module(stage_name, interactive=True)
    virtual_module = sys.modules[virtual_module_name]

    print(f"\n{virtual_module_name.split('.')[-1]}.pyi")

    signature = inspect.signature(created_function)
    stub_docstring = (
        f'    """{created_function.__doc__}"""'  # inspect.getdoc(created_function)
    )
    stub_string = f"def {function_name}{signature.format()}:\n{stub_docstring}"
    print(stub_string)

    print()

    setattr(virtual_module, function_name, created_function)
