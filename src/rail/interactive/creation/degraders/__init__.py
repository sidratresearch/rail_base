"""Module docstring for interactive degraders"""

import sys

from rail.utils.interactive_utils import (
    _attatch_interactive_function,
    _create_virtual_submodules,
    _get_stage_module,
    _stage_names,
)

_degrader_stages = [
    stage
    for stage in _stage_names
    if _get_stage_module(stage, interactive=True).startswith(__name__)
]
_current_module = sys.modules[__name__]

# for testing
_degrader_stages = _degrader_stages[:2] + _degrader_stages[-1:]

_stage_module_dict = _create_virtual_submodules(_current_module, _degrader_stages)


for _stage_name in _degrader_stages:
    _attatch_interactive_function(_stage_module_dict, _stage_name)
