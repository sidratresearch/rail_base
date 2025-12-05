import functools
import inspect
import types
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import rail.stages
from rail.core import RailEnv
from rail.core.stage import RailStage

rail.stages.import_and_attach_all(silent=True)

_stage_names = list(RailStage.pipeline_stages.keys())
_stage_names = [
    i
    for i in _stage_names
    if i not in RailEnv._base_stages_names  # pylint: disable=protected-access
]
_stage_names.sort()

_SHOW_STUB_CONTENT = False


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


@dataclass
class VirtualModule:
    module: types.ModuleType
    children: dict[str, str]
    parent: str


def _create_virtual_submodules(module: types.ModuleType, stage_names: list[str]):
    stage_module_names = [
        _get_stage_module(stage, interactive=True) for stage in stage_names
    ]
    stage_module_names = sorted(list(set(stage_module_names)))

    # get a recursive version of the names
    recursive_module_names = []
    for module_name in stage_module_names:
        relative_name = module_name.replace(module.__name__, "")[1:]
        parts = relative_name.split(".")
        for depth in range(len(parts)):
            relative_name = ".".join(parts[: depth + 1])
            if relative_name not in recursive_module_names:
                recursive_module_names.append(module.__name__ + "." + relative_name)

    # populate a dictionary of virtual modules, keeping track of relationships
    virtual_modules = {}
    for virtual_module_name in recursive_module_names:
        virtual_modules[virtual_module_name] = VirtualModule(
            module=types.ModuleType(virtual_module_name),
            children=[],
            parent=module.__name__,
        )
        if len(virtual_module_name.split(".")) != len(module.__name__.split(".")) + 1:
            parent = virtual_modules[
                virtual_module_name[: virtual_module_name.rindex(".")]
            ]
            virtual_modules[virtual_module_name].parent = parent.module.__name__
            parent.children.append(virtual_modules[virtual_module_name].module.__name__)

    # print the import section of type stubs for child and top level virtual modules
    if _SHOW_STUB_CONTENT:
        for vm_name, vm_VM in virtual_modules.items():
            print("\n" + vm_name.replace(".", "/") + ".pyi")
            for child_module_name in vm_VM.children:
                print(f"from . import {child_module_name.split(".")[-1]}")
        print("\n" + module.__path__[0].strip() + "/__init__.pyi")
        for vm_name, vm_VM in virtual_modules.items():
            if vm_VM.parent == module.__name__:
                print(f"from . import {vm_name.split('.')[-1]}")

    # attatch virtual modules to their correct parents
    for vm_name, vm_VM in virtual_modules.items():
        if vm_VM.parent == module.__name__:
            setattr(module, vm_name.split(".")[-1], vm_VM.module)
        else:
            parent = virtual_modules[vm_VM.parent]
            setattr(parent.module, vm_name.split(".")[-1], vm_VM.module)

    return virtual_modules


def _create_interactive_docstring(stage_name: str):
    stage_definition = _get_stage_definition(stage_name)

    class_docstring = stage_definition.__doc__
    epf_docstring = getattr(
        stage_definition, stage_definition.entrypoint_function
    ).__doc__

    class_summary = class_docstring[
        : class_docstring.index("\nParameters\n----------")
    ].strip()
    class_parameters = (
        class_docstring[class_docstring.index("\nParameters\n----------") + 22 :]
        .strip()
        .replace("\n\n", "\n")
    )
    epf_summary = epf_docstring[
        : epf_docstring.index("\nParameters\n----------")
    ].strip()
    epf_parameters = epf_docstring[
        epf_docstring.index("\nParameters\n----------") : epf_docstring.index(
            "\nReturns\n-------"
        )
    ].strip()
    epf_returns = epf_docstring[epf_docstring.index("\nReturns\n-------") :].strip()

    # print(f">>>>>>>>>>>>>\n{class_summary}\n<<<<<<<<<<<<<<<")
    # print(f">>>>>>>>>>>>>\n{epf_summary}\n<<<<<<<<<<<<<<<")
    # print(f">>>>>>>>>>>>>\n{epf_parameters}\n<<<<<<<<<<<<<<<")
    # print(f">>>>>>>>>>>>>\n{class_parameters}\n<<<<<<<<<<<<<<<")
    # print(f">>>>>>>>>>>>>\n{epf_returns}\n<<<<<<<<<<<<<<<")

    source_file = inspect.getsourcefile(stage_definition)

    docstring = f"""{class_summary}

{epf_summary}

This function was generated from {source_file}

{epf_parameters}
{class_parameters}

{epf_returns}"""

    if stage_definition.extra_interactive_documentation is not None:
        docstring += "\n" + stage_definition.extra_interactive_documentation

    return docstring


def _attatch_interactive_function(stage_module_dict, stage_name: str) -> None:
    stage_definition = _get_stage_definition(stage_name)
    function_name = stage_definition.interactive_function
    created_function: Callable = functools.partial(
        _interactive_factory, stage_definition
    )
    created_function.__doc__ = _create_interactive_docstring(stage_name)

    virtual_module_name = _get_stage_module(stage_name, interactive=True)
    virtual_module = stage_module_dict[virtual_module_name]

    if _SHOW_STUB_CONTENT:
        print(f"\n{virtual_module_name.split('.')[-1]}.pyi")
        signature = inspect.signature(created_function)
        stub_docstring = (
            f'    """{created_function.__doc__}"""'  # inspect.getdoc(created_function)
        )
        stub_string = f"def {function_name}{signature.format()}:\n{stub_docstring}"
        print(stub_string)
        print()

    setattr(virtual_module.module, function_name, created_function)
