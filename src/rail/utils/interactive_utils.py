"""
Utility functions for the rail.interactive module.
"""

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


@dataclass
class VirtualModule:
    """A wrapper class to hold a code-created module/namespace, as well as it's
    relationships to other modules"""

    module: types.ModuleType
    children: dict[str, str]
    parent: str


DOCSTRING_FORMAT = """
{class_summary}

---

{function_summary}

---

This function was generated from the function {source_file}

{function_parameters}
{class_parameters}

{function_returns}

{extra_documentation}
"""


def _interactive_factory(rail_stage: type[RailStage], **kwargs) -> Any:
    """Create the actual interactive function for a RAIL stage

    Parameters
    ----------
    rail_stage : type[RailStage]
        The stage being operated on

    Returns
    -------
    Any
        This function returns the result of calling the stage's entrypoint function
        (after calling make_stage)
    """
    instance = rail_stage.make_stage(**kwargs)
    entrypoint_function_name = instance.entrypoint_function
    entrypoint_function: Callable = getattr(instance, entrypoint_function_name)
    return entrypoint_function(**kwargs)


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
        return module.replace("rail.", "rail.interactive.", count=1)
    return module


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


def _split_docstring(
    docstring: str, include_headers: bool = True
) -> collections.defaultdict[str, str]:
    """Split the docstring into sections based on specific numpy-style headers.

    Does some whitespace formatting on the returned sections

    Parameters
    ----------
    docstring : str
        The raw docstring (.__doc__, inspect.getdoc, pydoc.doc)
    include_headers : bool, optional
        Whether or not to include the section header in the returned string, by default
        True

    Returns
    -------
    collections.defaultdict[str, str]
        Dictionary of {header: content}
    """

    result = collections.defaultdict(list)
    docstring_lines = docstring.splitlines()
    sections = ["Summary", "Parameters", "Returns"]

    # add lines to `result` one at a time, tracking which section is being used
    line_no = 0
    current_section = 0
    while line_no < len(docstring_lines) - 1:
        if _is_section_header(line_no, docstring_lines):
            current_section += 1
            if include_headers:
                result[sections[current_section]].append(docstring_lines[line_no])
                result[sections[current_section]].append(docstring_lines[line_no + 1])
            line_no += 2
        else:
            result[sections[current_section]].append(docstring_lines[line_no])
            line_no += 1
    result[sections[current_section]].append(
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

    splitting_headers = [
        "Parameters",
        "Returns",
    ]  # very small subset of numpydoc.validate.ALLOWED_SECTIONS

    current_line = docstring_lines[line_no].strip()
    if current_line in splitting_headers:
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
    class_sections = _split_docstring(class_docstring, include_headers=False)
    epf_sections = _split_docstring(epf_docstring)
    source_file = ".".join(
        [stage_definition.__module__, stage_name, stage_definition.entrypoint_function]
    )

    # assemble the docstring
    docstring = DOCSTRING_FORMAT.format(
        class_summary=class_sections["Summary"],
        function_summary=epf_sections["Summary"],
        source_file=source_file,
        function_parameters=epf_sections["Parameters"].replace("\n\n", "\n"),
        class_parameters=class_sections["Parameters"].replace("\n\n", "\n"),
        function_returns=epf_sections["Returns"],
        extra_documentation=(
            stage_definition.extra_interactive_documentation
            if stage_definition.extra_interactive_documentation is not None
            else ""
        ),
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

    # wrap and then re-indent the docstring
    indent_size = 4
    max_line_length = 88
    docstring = textwrap.indent(
        _wrap_docstring(
            docstring.strip(),
            max_line_length=max_line_length - indent_size,
            line_filter=param_annotation_filter,
        ),
        "" * indent_size,
    )

    return docstring


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
    created_function: Callable = functools.partial(
        _interactive_factory, stage_definition
    )
    created_function.__doc__ = _create_interactive_docstring(stage_name)

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
        buffer = " " * 4 + '"""'
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
        path = path.with_name(f"generated_{path.name}")
        path.write_text(content)
        black.format_file_in_place(
            path,
            fast=False,
            mode=black.Mode(is_pyi=True),
            write_back=black.WriteBack.YES,
        )
        isort.api.sort_file(path, quiet=True, profile="black")

        print(f"Created {str(path)}")


def _initialize_interactive_module(calling_module_name: str, write_stubs: bool = False):
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

    # for testing
    relevant_stages = relevant_stages[:2] + relevant_stages[-1:]

    virtual_module_dict = _create_virtual_submodules(calling_module, relevant_stages)

    for stage_name in relevant_stages:
        _attatch_interactive_function(virtual_module_dict, stage_name)

    if write_stubs:
        _write_stubs(calling_module, relevant_stages, virtual_module_dict)
