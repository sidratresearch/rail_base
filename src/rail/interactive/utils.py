import functools
import types
from collections.abc import Callable

import rail.stages
from rail.core import RailEnv
from rail.core.stage import RailStage

rail.stages.import_and_attach_all()
stage_names = list(RailStage.pipeline_stages.keys())
stage_names = [
    i
    for i in stage_names
    if i not in RailEnv._base_stages_names  # pylint: disable=protected-access
]
stage_names.sort()


def interactive_factory(rail_stage: RailStage, **kwargs) -> Callable:
    instance = rail_stage.make_stage(**kwargs)
    entrypoint_function_name = instance.entrypoint_function
    entrypoint_function: Callable = getattr(instance, entrypoint_function_name)
    return entrypoint_function(**kwargs)


def _get_all_stage_names() -> list[str]:
    return stage_names


def _get_stage_definition(stage_name: str) -> type:
    return RailStage.pipeline_stages[stage_name][0]


def _get_stage_module(stage_name: str, interactive: bool = False) -> str:
    module = _get_stage_definition(stage_name).__module__
    if interactive:
        return module.replace("rail.", "rail.interactive.", count=1)
    return module


def _attatch_interactive_function(module: types.ModuleType, stage_name: str):
    stage_definition = _get_stage_definition(stage_name)
    function_name = stage_definition.interactive_function
    created_function: Callable = functools.partial(
        interactive_factory, stage_definition
    )

    setattr(module, function_name, created_function)
