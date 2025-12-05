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

import black

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
    instance = rail_stage.make_stage(**kwargs)
    entrypoint_function_name = instance.entrypoint_function
    entrypoint_function: Callable = getattr(instance, entrypoint_function_name)
    return entrypoint_function(**kwargs)


def _get_stage_definition(stage_name: str) -> type[RailStage]:
    return RailStage.pipeline_stages[stage_name][0]


def _get_stage_module(stage_name: str, interactive: bool = False) -> str:
    module = _get_stage_definition(stage_name).__module__
    if interactive:
        return module.replace("rail.", "rail.interactive.", count=1)
    return module


def _create_virtual_submodules(
    module: types.ModuleType, stage_names: list[str]
) -> dict[str, VirtualModule]:
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

    # attatch virtual modules to their correct parents
    for vm_name, vm_VM in virtual_modules.items():
        if vm_VM.parent == module.__name__:
            setattr(module, vm_name.split(".")[-1], vm_VM.module)
        else:
            parent = virtual_modules[vm_VM.parent]
            setattr(parent.module, vm_name.split(".")[-1], vm_VM.module)

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

    line_no = 0
    current_section = 0
    sections = ["Summary", "Parameters", "Returns"]
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
    result[sections[current_section]].append(docstring_lines[line_no])

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


def _create_interactive_docstring(stage_name: str) -> str:
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

    docstring = textwrap.indent(docstring.strip(), " " * 4)

    return docstring


def _attatch_interactive_function(
    stage_module_dict: dict[str, VirtualModule], stage_name: str
) -> None:
    stage_definition = _get_stage_definition(stage_name)
    function_name = stage_definition.interactive_function
    created_function: Callable = functools.partial(
        _interactive_factory, stage_definition
    )
    created_function.__doc__ = _create_interactive_docstring(stage_name)

    virtual_module_name = _get_stage_module(stage_name, interactive=True)
    virtual_module = stage_module_dict[virtual_module_name]

    setattr(virtual_module.module, function_name, created_function)


def _get_stub_path(
    stub_directory: Path,
    virtual_module_name: str | None = None,
) -> Path:
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

    Parameters
    ----------
    module : types.ModuleType
        The RAIL module that the interactive functions are children of
    stage_names : list[str]
        Names of RAIL stages that have interactive functions
    virtual_modules : dict[str, VirtualModule]
        The code-created namespaces that the interactive functions live in
    """

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
