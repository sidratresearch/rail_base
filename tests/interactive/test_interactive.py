"""
Not sure about the placement of this file
"""

import collections
import inspect

from rail.core.stage import RailStage
from rail.utils.interactive.docstring_utils import (
    InteractiveParameter,
    _parse_annotation_string,
    _split_docstring,
)
from rail.utils.interactive.initialize_utils import STAGE_NAMES, _get_stage_definition


def test_interactive_function_names() -> None:
    """Check for unset names and name collisions in the `interactive_function` attribute
    of RailStages."""
    if_name_attribute = "interactive_function"
    function_name_uses = collections.defaultdict(
        list  # {"name of interactive fn":[stages using that name, ...]}
    )
    exists_stage_without_attribute = False
    exists_name_with_multiple_uses = False

    # initial loop through stages
    for stage_name in STAGE_NAMES:
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


def validate_return_annotation(
    stage_name: str,
    stage_definition: type[RailStage],
    return_elements: list[InteractiveParameter],
) -> None:
    # grab the different return types
    from_docstring = [r.annotation for r in return_elements]
    from_inspect = inspect.signature(
        getattr(stage_definition, stage_definition.entrypoint_function)
    ).return_annotation
    from_ceci = [i[1] for i in stage_definition.outputs]

    warning_start = "Return type annotation for entrypoint function"

    if from_inspect == inspect.Parameter.empty:
        raise ValueError(f"{warning_start} is missing in {stage_name}")

    if isinstance(
        from_inspect, type
    ):  # a class, rather than, say, dict[str, str] which is a GenericAlias

        # if we have a single ceci output, make sure it matches the annotation
        if (len(from_ceci) == 1) and (from_inspect != from_ceci[0]):
            print(
                f"WARNING: {warning_start} doesn't match the output property of {stage_name}"
            )
        if len(from_ceci) > 1:
            print(
                f"WARNING: {warning_start} cannot be checked against multiple ceci outputs defined in {stage_name}"  # pylint: disable=line-too-long
            )

        from_inspect = str(from_inspect).split("'")[1]

        # if we have a single docstring item, make sure it matches the annotation
        if len(from_docstring) == 1:
            from_docstring = from_docstring[0]
            if from_inspect.endswith(from_docstring):  # Ensemble & Ensemble
                return
            if "." in from_docstring:  # Ensemble and qp.Ensemble
                docstring_final = from_docstring[from_docstring.rindex(".") + 1 :]
                if from_inspect.endswith(docstring_final):
                    return
            raise ValueError(
                f"{warning_start} doesn't match the docstring in {stage_name} (docstring={repr(from_docstring)}, annotation={from_inspect})"  # pylint: disable=line-too-long
            )
        if len(from_docstring) > 1:
            print(
                f"WARNING: {warning_start} cannot be checked against multiple docstring entries in {stage_name}"  # pylint: disable=line-too-long
            )
    elif from_inspect is None:
        return
    else:
        print(f"WARNING: {warning_start} is too complex to be checked in {stage_name}")


def test_return_annotations() -> None:
    for stage_name in STAGE_NAMES:
        stage_definition = _get_stage_definition(stage_name)
        epf_docstring = getattr(
            stage_definition, stage_definition.entrypoint_function
        ).__doc__
        epf_sections = _split_docstring(epf_docstring)
        return_elements = _parse_annotation_string(epf_sections["Returns"])

        validate_return_annotation(stage_name, stage_definition, return_elements)
