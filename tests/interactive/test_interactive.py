"""
Not sure about the placement of this file
"""

import collections

from rail.utils.interactive_utils import _get_stage_definition, _stage_names


def test_interactive_function_names() -> None:
    if_name_attribute = "interactive_function"
    function_name_uses = collections.defaultdict(
        list  # {"name of interactive fn":[stages using that name, ...]}
    )
    exists_stage_without_attribute = False
    exists_name_with_multiple_uses = False

    # initial loop through stages
    for stage_name in _stage_names:
        # get and store the name
        interactive_function_name = getattr(
            _get_stage_definition(stage_name), if_name_attribute
        )

        # run the is None check for this stage
        if interactive_function_name is None:
            print(f"{if_name_attribute} is not set for RailStage {stage_name}")
            exists_stage_without_attribute = True

        else:
            function_name_uses[interactive_function_name].append(stage_name)
    assert not exists_stage_without_attribute

    # secondary loop to check for duplicates
    for interactive_function_name, stages in function_name_uses.items():
        if len(stages) > 1:
            msg = "{if_name_attribute} = {function} is repeated in mutiple stages: {stages}"
            print(
                msg.format(
                    if_name_attribute=if_name_attribute,
                    function=interactive_function_name,
                    stages=", ".join(stages),
                )
            )
            exists_name_with_multiple_uses = True
    assert not exists_name_with_multiple_uses
