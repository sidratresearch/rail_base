"""
Utility functions for the rail.interactive module.
"""

# pylint: disable=too-many-lines

import collections
import functools
import inspect
import sys
import textwrap
import types
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ceci.config import StageConfig, StageParameter

import rail.stages
from rail.core import RailEnv
from rail.core.data import ModelHandle, PqHandle, QPHandle
from rail.core.stage import RailStage
from rail.utils.path_utils import RAILDIR, unfind_rail_file

rail.stages.import_and_attach_all(silent=True)

_stage_names = list(RailStage.pipeline_stages.keys())
_stage_names = [
    i
    for i in _stage_names
    if i not in RailEnv._base_stages_names  # pylint: disable=protected-access
]
_stage_names.sort()

DOCSTRING_LINE_LENGTH = 88
DOCSTRING_INDENTATION = 4

# parameters that are passed to make_stage for all stages
GLOBAL_INTERACTIVE_PARAMETERS = {"output_mode": "return", "force_exact": True}


@dataclass
class VirtualModule:
    """A wrapper class to hold a code-created module/namespace, as well as it's
    relationships to other modules"""

    module: types.ModuleType
    children: dict[str, str]
    parent: str


# INTERACTIVE_DO: is there any case where an interactive function might not return? no, right?
DOCSTRING_FORMAT = """
{class_summary}

---

{function_summary}

---

This function was generated from the function {source_file}

Parameters
----------
{parameters}

Returns
-------
{returns}

{extra_documentation}
"""

SECTION_HEADERS = [
    "Summary",
    "Parameters",
    "Returns",
    "Notes",
]  # very small subset of numpydoc.validate.ALLOWED_SECTIONS


def _interactive_factory(
    rail_stage: type[RailStage], function_input_is_wrapped: bool, **kwargs
) -> Any:
    """Create the actual interactive function for a RAIL stage

    Parameters
    ----------
    rail_stage : type[RailStage]
        The stage being operated on
    function_input_is_wrapped : bool
        Whether or not the interactive version of the entrypoint function has wrapped up
        multiple positional parameters into a dictionary, that needs to be unwrapped
        when passing it onwards

    Returns
    -------
    Any
        This function returns the result of calling the stage's entrypoint function
        (after calling make_stage)
    """
    # extract the input kwarg, and turn it into the appropriate DataHandle
    entrypoint_inputs = kwargs.pop("input")

    for key, value in GLOBAL_INTERACTIVE_PARAMETERS.items():
        if key in kwargs:
            raise ValueError(f"In rail.interactive, {key} is set to {value}")

    instance = rail_stage.make_stage(**kwargs, **GLOBAL_INTERACTIVE_PARAMETERS)
    entrypoint_function_name = instance.entrypoint_function
    entrypoint_function: Callable = getattr(instance, entrypoint_function_name)

    if function_input_is_wrapped:
        output = entrypoint_function(**entrypoint_inputs, **kwargs)
    else:
        output = entrypoint_function(entrypoint_inputs, **kwargs)

    # convert output FROM a DataHandle into pure data, need to handle the case of
    # multiple outputs - use each tag as dict key
    interactive_output = {}

    # single item output
    if len(rail_stage.outputs) == 1:
        tag, class_ = rail_stage.outputs[0]

        if class_ == PqHandle:
            interactive_output[tag] = output.data
        elif class_ == ModelHandle:
            interactive_output[tag] = output.data
        elif class_ == QPHandle:
            interactive_output[tag] = output.data
        else:  # not impl
            print(class_)
            interactive_output[tag] = "Output class not impl"

        # INTERACTIVE_DO: Testing line
        print(
            f"{rail_stage} output type is {class_}, output.data has type {type(output.data)}"
        )

    else:  # not impl
        # multi item output
        print("MULTI ITEM OUTPUT", rail_stage.output_tags(), rail_stage.outputs)
        for tag, class_ in rail_stage.outputs:
            pass
        return rail_stage.outputs

    return interactive_output


def _get_stage_definition(stage_name: str) -> type[RailStage]:
    """Fetch the original class definition for a RAIL stage from its name

    Parameters
    ----------
    stage_name : str
        Name of the RAIL stage class

    Returns
    -------
    type[RailStage]
        The class definition
    """
    return RailStage.pipeline_stages[stage_name][0]


def _get_stage_module(stage_name: str, interactive: bool = False) -> str:
    """Get the name of the module from which you would import the given RAIL stage

    Parameters
    ----------
    stage_name : str
        Name of the RAIL stage class
    interactive : bool, optional
        Whether this would be imported from rail.interactive instead of rail, by default False

    Returns
    -------
    str
        Absolute import path
    """
    module = _get_stage_definition(stage_name).__module__
    if interactive:
        return module.replace("rail.", "rail.interactive.", 1)
    return module


def _get_virtual_submodule_names(
    module: types.ModuleType, stage_names: list[str]
) -> list[str]:
    """Get a list of all of the submodules of `module` that interactive will have

    Parameters
    ----------
    module : types.ModuleType
        The module to get children of
    stage_names : list[str]
        The stages that we need locations for

    Returns
    -------
    list[str]
        A sorted, unique list of module names, including intermediaries between `module`
        and the definition of each stage
    """
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

    return sorted(list(set(recursive_module_names)))


def _create_virtual_submodules(
    module: types.ModuleType, stage_names: list[str]
) -> dict[str, VirtualModule]:
    """Create all the relevant child namespaces of `module` in which the interactive
    functions will live.

    Parameters
    ----------
    module : types.ModuleType
        The parent module
    stage_names : list[str]
        RAIL stages which will have interactive functions

    Returns
    -------
    dict[str, VirtualModule]
        All of the created namespaces
    """
    recursive_module_names = _get_virtual_submodule_names(module, stage_names)

    # populate a dictionary of virtual modules, keeping track of relationships
    virtual_modules = {}
    for virtual_module_name in recursive_module_names:
        virtual_modules[virtual_module_name] = VirtualModule(
            module=types.ModuleType(virtual_module_name),
            children=[],
            parent=module.__name__,
        )

        # assign parent/child relationships if necessary
        if len(virtual_module_name.split(".")) != len(module.__name__.split(".")) + 1:
            parent = virtual_modules[
                virtual_module_name[: virtual_module_name.rindex(".")]
            ]
            virtual_modules[virtual_module_name].parent = parent.module.__name__
            parent.children.append(virtual_modules[virtual_module_name].module.__name__)

    # attatch virtual modules to their correct parents
    for name, virtual_module in virtual_modules.items():
        if virtual_module.parent == module.__name__:
            setattr(module, name.split(".")[-1], virtual_module.module)
        else:
            parent = virtual_modules[virtual_module.parent]
            setattr(parent.module, name.split(".")[-1], virtual_module.module)

    return virtual_modules


def _split_docstring(docstring: str) -> collections.defaultdict[str, str]:
    """Split the docstring into sections based on specific numpy-style headers.

    Does some whitespace formatting on the returned sections

    Parameters
    ----------
    docstring : str
        The raw docstring (.__doc__, inspect.getdoc, pydoc.doc)

    Returns
    -------
    collections.defaultdict[str, str]
        Dictionary of {header: content}
    """

    result = collections.defaultdict(list)
    docstring_lines = docstring.splitlines()

    # add lines to `result` one at a time, tracking which section is being used
    line_no = 0
    current_section = 0
    while line_no < len(docstring_lines) - 1:
        if _is_section_header(line_no, docstring_lines):
            current_section = SECTION_HEADERS.index(docstring_lines[line_no].strip())
            line_no += 2
        else:
            result[SECTION_HEADERS[current_section]].append(docstring_lines[line_no])
            line_no += 1
    result[SECTION_HEADERS[current_section]].append(
        docstring_lines[line_no]
    )  # add the final line

    # merge list items together
    joined_result = collections.defaultdict(str)
    for title, lines in result.items():
        joined_result[title] = "\n".join(lines).replace("\n\n\n", "\n\n").strip()
    return joined_result


def _is_section_header(line_no: int, docstring_lines: list[str]) -> bool:
    """Check whether a given line is the start (text line) of a header.

    Headers are checked against a list of "splitting headers", and a line containing
    exactly this text, followed be a line of hyphens of the same length indicates a
    header

    This roughly follows the numpydoc function NumpyDocString._is_at_section()

    Parameters
    ----------
    line_no : int
        The line number to check
    docstring_lines : list[str]
        All lines in the docstring

    Returns
    -------
    bool
        Whether this line number starts a header
    """

    current_line = docstring_lines[line_no].strip()
    if current_line in SECTION_HEADERS:
        next_line = docstring_lines[line_no + 1].strip()
        return next_line == ("-" * len(current_line))
    return False


def _wrap_docstring(
    text: str,
    max_line_length: int,
    line_filter: Callable[[int, list[str]], bool] | None = None,
) -> str:
    """Wrap a docstring (or portion thereof) to a given length

    Parameters
    ----------
    text : str
        The text to wrap
    max_line_length : int
        The width to wrap at
    line_filter : Callable[[int, list[str]], bool] | None, optional
        A filter function to check if a line should skip wrapping, by default None.
        The function takes the line number and the full text (for multi-line analysis)
        and returns True if this line should skip wrapping, and False if this line
        should be wrapped. This function returning True (skip) will override the line
        length check, so is a way to force long lines to not wrap

    Returns
    -------
    str
        The wrapped text
    """
    wrapped_lines = []

    text = text.replace("\t", " " * 4)  # probably not necessary
    lines = text.splitlines()

    for i, line in enumerate(lines):
        # exit early if the line is short, or the filter says so
        line_is_short = len(line) <= max_line_length
        line_skips = line_filter(i, lines) if line_filter is not None else False
        if line_is_short or line_skips:
            wrapped_lines.append(line)
            continue

        unindented = line.lstrip()
        indent_size = len(line) - len(unindented)

        # wrap the text, keeping the indent width in mind
        wrapped_line = "\n".join(
            textwrap.wrap(unindented, width=max_line_length - indent_size)
        )

        # re-indent to the original depth, and save the line
        wrapped_lines.append(textwrap.indent(wrapped_line, " " * indent_size))

    return "\n".join(wrapped_lines)


def _param_annotion_wrap_filter(
    parameters_section_header: int,
    blank_lines: list[int],
    lineno: int,
    docstring_lines: list[str],
) -> bool:
    """Filter out annotation (not description) lines in the Parameters section of a
    docstring from being wrapped.

    Needs to be applied to a docstring BEFORE any indentation, as this uses the fact
    that annotations are un-indented.
    This also isn't applied to the Returns section (or any others that might have
    annotation-style items that shouldn't be wrapped; because Parameters is the only
    section we guarantee the existence of in an isolate-able fashion.

    Parameters
    ----------
    parameters_section_header : int
        The line number where the Parameters header is
    blank_lines : list[int]
        Empty lines in the docstring
    lineno : int
        The line number of the docstring to check
    docstring_lines : list[str]
        The entire docstring, split into lines

    Returns
    -------
    bool
        Whether to skip line wrapping because this is an annotation (True) or not (False)
    """

    # lines up to and including the parameter header are not parameter annotations
    if lineno <= parameters_section_header + 1:
        return False

    # check if we've left the parameters section
    if max(blank_lines) > parameters_section_header:
        # there exist blank lines after the param header, these should denote a new
        # section (though that new section might not have a header, which is why we're
        # checking with newlines)
        parameters_section_end = [
            i for i in blank_lines if i > parameters_section_header
        ][-1]
        if parameters_section_end < lineno:
            return False  # passed the end of the param section

    # we are inside the parameters section
    line = docstring_lines[lineno]
    unindented = line.lstrip()

    # if true this is a parameter annotation (not the description of it), skip wrapping
    return len(line) == len(unindented)


def _handle_default_path(path: str | Path) -> str:
    if isinstance(path, Path):
        path = str(path)

    if path.startswith(RAILDIR):
        return path.replace(RAILDIR, "rail.utils.path_utils.RAILDIR")
    if path.startswith("/"):
        return unfind_rail_file(path)

    return path


def _handle_dictionary_paths(dictionary: dict[str, Any]) -> dict[str, Any]:
    for key, value in dictionary.items():
        if isinstance(value, (str, Path)):
            dictionary[key] = _handle_default_path(value)
        if isinstance(value, dict):
            dictionary[key] = _handle_dictionary_paths(value)
    return dictionary


@dataclass
class InteractiveParameter:
    name: str | None
    annotation: str
    description: str
    is_required: bool = True

    def __str__(self) -> str:
        description = textwrap.indent(self.description, " " * DOCSTRING_INDENTATION)
        if self.name is None:
            return f"{self.annotation}\n{description}"
        return f"{self.name} : {self.annotation}\n{description}"

    @classmethod
    def from_ceci(cls, name: str, ceci_param: Any) -> "InteractiveParameter":
        if isinstance(ceci_param, StageParameter):
            return cls.from_ceci_parameter(name, ceci_param)
        if isinstance(ceci_param, StageConfig):
            return cls.from_ceci_parameter(name, dict.__getitem__(ceci_param, name))

        return cls(
            name=name,
            annotation="unknown type, optional",
            description=f"Default: {ceci_param}",
            is_required=False,
        )

    @classmethod
    def from_ceci_parameter(
        cls, name: str, ceci_param: StageParameter
    ) -> "InteractiveParameter":
        dtype_name = "unknown type"
        if ceci_param.dtype is not None:
            dtype_name = ceci_param.dtype.__name__

        description = " ".join(
            textwrap.wrap(
                ceci_param.msg, width=DOCSTRING_LINE_LENGTH - DOCSTRING_INDENTATION * 2
            )
        )
        annotation = dtype_name

        if not ceci_param.required:
            annotation += ", optional"
            default_value = ceci_param.default
            max_default_length = (
                DOCSTRING_LINE_LENGTH - DOCSTRING_INDENTATION * 2 - len("Default: ")
            )

            # handle default values that might be paths
            if isinstance(ceci_param.default, (str, Path)):
                default_value = _handle_default_path(ceci_param.default)
            if isinstance(ceci_param.default, dict):
                default_value = _handle_dictionary_paths(ceci_param.default)

            # truncate long default values
            if (len(str(default_value)) > max_default_length) and (
                isinstance(default_value, (dict, list))
            ):
                end = str(default_value)[-1]
                shortened_string = textwrap.shorten(
                    str(default_value), width=max_default_length - 2, placeholder="..."
                )
                default_value = f"{shortened_string}{end}"

            description += f"\nDefault: {default_value}"

        return InteractiveParameter(
            name=name,
            annotation=annotation,
            description=description.strip(),  # don't start with newline if cece msg=""
            is_required=ceci_param.required,
        )


def _create_parameters_section(
    stage_definition: type[RailStage], stage_name: str, epf_parameter_string: str
) -> str:

    # Read in parameters to both the class and EPF
    class_parameters = [
        InteractiveParameter.from_ceci(name, ceci_param)
        for name, ceci_param in stage_definition.config_options.items()
    ]
    epf_inspected_parameters = inspect.signature(
        getattr(stage_definition, stage_definition.entrypoint_function)
    ).parameters.values()
    epf_parameters = _parse_annotation_string(
        epf_parameter_string, epf_inspected_parameters
    )

    # INTERACTIVE-DO: turn this into a proper test somewhere
    if "kwargs" not in [i.name for i in epf_inspected_parameters]:
        raise ValueError(f"Missing kwargs in interactive function of {stage_name}")

    # Handle positional parameters to EPF
    input_is_wrapped = (
        False  # flag for the interactive function, indicating whether "input" is a dict
    )
    input_parameter_names = [
        i.name
        for i in epf_inspected_parameters
        if i.name not in ["self", "kwargs"] and i.default == inspect.Parameter.empty
    ]
    input_parameters_indices = [
        i
        for i, param in enumerate(epf_parameters)
        if param.name in input_parameter_names
    ]
    if len(input_parameters_indices) == 1:
        input_parameter = epf_parameters.pop(input_parameters_indices[0])
        input_parameter.name = "input"
        epf_parameters.insert(0, input_parameter)
    elif len(input_parameters_indices) > 1:
        input_is_wrapped = True
        annotation_entries = []
        description_entries = ["Dictionary of input data with the following keys:"]
        for i, index in enumerate(input_parameters_indices):
            param = epf_parameters.pop(index - i)  # adjust index as we shorten the list
            annotation_entries.append(f'"{param.name}": {param.annotation}')
            description_entries.append(
                f"{param.name}: {param.annotation} - {param.description.replace('\n',' ')}"
            )
        annotation = f"dict[{', '.join(annotation_entries)}]"
        input_parameter = InteractiveParameter(
            name="input",
            annotation=annotation,
            description="\n".join(description_entries),
        )
        epf_parameters.insert(0, input_parameter)

    # Class parameters
    existing_names = [p.name for p in epf_parameters]
    for parameter in class_parameters:
        if parameter.name not in existing_names:
            epf_parameters.append(parameter)
        else:
            print(
                f"Warning - parameter '{parameter.name}' is duplicated in config_options and EPF of {stage_name}"  # pylint: disable=line-too-long
            )

    # remove the parameters that we force the values of
    epf_parameters = [
        p for p in epf_parameters if p.name not in GLOBAL_INTERACTIVE_PARAMETERS
    ]

    return (
        "\n".join([str(i) for i in _sort_parameters(epf_parameters)]),
        input_is_wrapped,
    )


def _sort_parameters(
    parameters: list[InteractiveParameter],
) -> list[InteractiveParameter]:
    input_parameter = None
    if parameters[0].name == "input":
        input_parameter = parameters.pop(0)

    remaining = sorted(parameters, key=lambda p: not p.is_required)

    if input_parameter is not None:
        remaining.insert(0, input_parameter)

    return remaining


def _parse_annotation_string(
    text: str, inspected_parameters: list[inspect.Parameter] | None = None
) -> list[InteractiveParameter]:
    lines = text.replace("\n\n", "\n").splitlines()
    annotation_linenos = []
    for i, line in enumerate(lines):
        if len(line.lstrip()) == len(line):
            annotation_linenos.append(i)

    parameters = []
    for i, lineno in enumerate(annotation_linenos):
        # get the item type and name (if supplied)
        if " : " in lines[lineno]:
            param_name, param_type = lines[lineno].split(" : ")

            if param_name.startswith("*"):
                continue
        else:
            param_name = None
            param_type = lines[lineno]

        # get the description
        if i < len(annotation_linenos) - 1:  # this is not the last annotation
            description_end = annotation_linenos[i + 1]
            description_lines = lines[lineno + 1 : description_end]
        else:
            description_lines = lines[lineno + 1 :]

        # check if there is a default
        is_required = False
        if inspected_parameters is not None:
            inspect_parameter = [
                p for p in inspected_parameters if p.name == param_name
            ][0]
            is_required = inspect_parameter.default == inspect.Parameter.empty

        parameters.append(
            InteractiveParameter(
                name=param_name,
                annotation=param_type,
                description="\n".join([j.strip() for j in description_lines]),
                is_required=is_required,
            )
        )

    return parameters


def _validate_return_annotations(
    stage_name: str,
    stage_definition: type[RailStage],
    return_elements: list[InteractiveParameter],
) -> None:
    # INTERACTIVE-DO: move this to the regular tests area
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


def _create_interactive_docstring(stage_name: str) -> str:
    """Merge the relevant information from the class and entrypoint function of a RAIL
    stage to create a docstring for the interactive function

    Parameters
    ----------
    stage_name : str
        Name of the RAIL stage

    Returns
    -------
    str
        The final docstring for the interactive function
    """
    stage_definition = _get_stage_definition(stage_name)

    # get the raw docstrings
    class_docstring = stage_definition.__doc__
    epf_docstring = getattr(
        stage_definition, stage_definition.entrypoint_function
    ).__doc__

    # do some pre-processing
    class_sections = _split_docstring(class_docstring)
    epf_sections = _split_docstring(epf_docstring)
    source_file = ".".join(
        [stage_definition.__module__, stage_name, stage_definition.entrypoint_function]
    )

    # handle the parameters
    parameters_content, input_is_wrapped = _create_parameters_section(
        stage_definition, stage_name, epf_sections["Parameters"]
    )

    # handle the return elements
    return_elements = _parse_annotation_string(epf_sections["Returns"])
    _validate_return_annotations(stage_name, stage_definition, return_elements)
    for item in return_elements:
        # Handle return annotations that are DataHandles
        if hasattr(rail.core.data, item.annotation):
            return_type = getattr(rail.core.data, item.annotation)
            if (
                return_type.interactive_type is None
                or return_type.interactive_description is None
            ):
                raise ValueError(
                    f"{return_type} used in {stage_name} is missing interactive details"
                )
                # INTERACTIVE_DO: move this to be a generic dev side test
            item.annotation = return_type.interactive_type
            item.description += "\n" + return_type.interactive_description
    if len(return_elements) == 0:
        return_elements = ["None"]
    returns_content = "\n".join([str(i) for i in return_elements])

    # handle any other content
    extra_documentation = ""
    for section_name, section_content in class_sections.items():
        if section_name not in ["Summary", "Parameters", "Returns"]:
            header = f"\n{section_name}\n{'-'*len(section_name)}"
            extra_documentation += f"{header}\n{section_content}"
    for section_name, section_content in epf_sections.items():
        if section_name not in ["Summary", "Parameters", "Returns"]:
            header = f"\n{section_name}\n{'-'*len(section_name)}"
            extra_documentation += f"{header}\n{section_content}"
    if stage_definition.extra_interactive_documentation is not None:
        extra_documentation += f"\n{stage_definition.extra_interactive_documentation}"

    # assemble the docstring
    docstring = DOCSTRING_FORMAT.format(
        class_summary=class_sections["Summary"],
        function_summary=epf_sections["Summary"],
        source_file=source_file,
        parameters=parameters_content,
        returns=returns_content,
        extra_documentation=extra_documentation,
    )

    # prepare to wrap the docstring
    docstring_lines = docstring.splitlines()
    section_headers = [
        i for i in range(len(docstring_lines)) if _is_section_header(i, docstring_lines)
    ]
    parameters_section_header = [
        i for i in section_headers if docstring_lines[i] == "Parameters"
    ][0]
    blank_lines = [
        i for i in range(len(docstring_lines)) if len(docstring_lines[i]) == 0
    ]
    param_annotation_filter = functools.partial(
        _param_annotion_wrap_filter, parameters_section_header, blank_lines
    )

    # wrap the docstring
    docstring = _wrap_docstring(
        docstring.strip(),
        max_line_length=DOCSTRING_LINE_LENGTH - DOCSTRING_INDENTATION,
        line_filter=param_annotation_filter,
    )

    return docstring, input_is_wrapped


def _attatch_interactive_function(
    stage_module_dict: dict[str, VirtualModule], stage_name: str
) -> None:
    """Create a wrapper function for a RAIL stage, and assign it to the appropriate namespace.

    Parameters
    ----------
    stage_module_dict : dict[str, VirtualModule]
        The set of namespaces that may be relevant
    stage_name : str
        The name of the RAIL stage class
    """
    stage_definition = _get_stage_definition(stage_name)
    function_name = stage_definition.interactive_function
    virtual_module_name = _get_stage_module(stage_name, interactive=True)
    virtual_module = stage_module_dict[virtual_module_name]

    # create the function
    docstring, function_input_is_wrapped = _create_interactive_docstring(stage_name)
    created_function: Callable = functools.partial(
        _interactive_factory, stage_definition, function_input_is_wrapped
    )
    created_function.__doc__ = docstring

    # INTERACTIVE_DO: testing
    if function_name is None:
        raise ValueError(f"{stage_name} has no interactive function name")
    setattr(virtual_module.module, function_name, created_function)


def _get_stub_path(
    stub_directory: Path,
    virtual_module_name: str | None = None,
) -> Path:
    """Get the final path to where a stub file should live

    Parameters
    ----------
    stub_directory : Path
        Parent directory for stub files
    virtual_module_name : str | None, optional
        The virtual module that's being written about if applicable, by default None

    Returns
    -------
    Path
        Path to the stub file
    """
    if virtual_module_name is not None:
        final_segment = virtual_module_name.split(".")[-1]
        filename = f"{final_segment}.pyi"
        return stub_directory / filename

    return stub_directory / "__init__.pyi"


def _write_stubs(
    module: types.ModuleType,
    stage_names: list[str],
    virtual_modules: dict[str, VirtualModule],
) -> None:
    """Write stub (type hint) files for interactive functions.

    Multiple runs of this function should result in identical stub files, and will not
    trigger a modification as read by Git.

    Parameters
    ----------
    module : types.ModuleType
        The RAIL module that the interactive functions are children of
    stage_names : list[str]
        Names of RAIL stages that have interactive functions
    virtual_modules : dict[str, VirtualModule]
        The code-created namespaces that the interactive functions live in
    """
    # formatters used for the stub files, imported here since these are only required
    # for developers
    # pylint: disable=import-outside-toplevel
    import black
    import isort

    stub_files = collections.defaultdict(list)
    stub_directory = Path(module.__path__[0])

    # import top level virtual modules
    stub = stub_files[_get_stub_path(stub_directory)]
    for vm_name, vm_VM in virtual_modules.items():
        if vm_VM.parent == module.__name__:
            stub.append(f"from . import {vm_name.split('.')[-1]}")

    # import child virtual modules from their parents
    for vm_name, vm_VM in virtual_modules.items():
        stub = stub_files[_get_stub_path(stub_directory, virtual_module_name=vm_name)]
        for child_module_name in vm_VM.children:
            stub.append(f"from . import {child_module_name.split(".")[-1]}")

    # add function stubs
    for stage_name in stage_names:
        virtual_module_name = _get_stage_module(stage_name, interactive=True)
        stage_definition = _get_stage_definition(stage_name)

        function_name = stage_definition.interactive_function
        virtual_module = virtual_modules[virtual_module_name].module
        created_function = getattr(virtual_module, function_name)

        signature = inspect.signature(created_function)
        buffer = " " * DOCSTRING_INDENTATION + '"""'
        docstring = f"{buffer}\n{created_function.__doc__}\n{buffer}"

        stub_path = _get_stub_path(
            stub_directory, virtual_module_name=virtual_module_name
        )
        stub_files[stub_path].append(
            f"def {function_name}{signature.format()}:\n{docstring}"
        )

    # merge lists to strings
    stub_files_strings: dict[Path, str] = {}
    for path, content in stub_files.items():
        joined_content = "\n".join(content)
        if ") -> Any:" in joined_content:
            joined_content = f"from typing import Any\n\n{joined_content}"
        stub_files_strings[path] = joined_content

    # write and format the file
    for path, content in stub_files_strings.items():
        path.write_text(content)
        black.format_file_in_place(
            path,
            fast=False,
            mode=black.Mode(is_pyi=True),
            write_back=black.WriteBack.YES,
        )
        isort.api.sort_file(path, quiet=True, profile="black")

        print(f"Created {str(path)}")


def _initialize_interactive_module(
    calling_module_name: str, write_stubs: bool = False
) -> None:
    """Create wrappers for RAIL stages as single-call functions for interactive use.

    Optionally create stub files to improve static analysis of these dynamically created functions.

    Parameters
    ----------
    calling_module_name : str
        The __name__ attribute of the module calling this function.
    write_stubs : bool, optional
        Whether to write stub files, by default False
    """

    calling_module = sys.modules[calling_module_name]

    # filter down all the RAIL stages to only ones which are children of this module
    relevant_stages = [
        stage
        for stage in _stage_names
        if _get_stage_module(stage, interactive=True).startswith(calling_module_name)
    ]

    virtual_module_dict = _create_virtual_submodules(calling_module, relevant_stages)

    for stage_name in relevant_stages:
        # print(f"Working on stage {stage_name}")
        _attatch_interactive_function(virtual_module_dict, stage_name)

    if write_stubs:
        _write_stubs(calling_module, relevant_stages, virtual_module_dict)
