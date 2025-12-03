"""Module docstring for interactive degraders"""

import sys

from ..utils import (
    _attatch_interactive_function,
    _get_all_stage_names,
    _get_stage_module,
)

__all__ = []

_stages = _get_all_stage_names()
_degrader_stages = [
    stage
    for stage in _stages
    if _get_stage_module(stage, interactive=True).startswith(__name__)
]
_current_module = sys.modules[__name__]


# for testing
_degrader_stages = _degrader_stages[:1]


for _stage_name in _degrader_stages:
    _attatch_interactive_function(_current_module, _stage_name)
