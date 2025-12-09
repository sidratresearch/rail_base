import collections
import importlib
import sys
from pathlib import Path

import black
import isort
import pytest

from rail.utils.interactive_utils import _initialize_interactive_module

interactive_modules = [
    "creation.degraders",
    "creation.engines",
    "estimation.algos",
    # "evaluation"
    # "evaluation.metrics"
]
interactive_path = Path("src/rail/interactive")
LOWEST_LEVEL_CONTENTS = """
\"\"\"Module docstring for interactive {name}\"\"\"

from rail.utils.interactive_utils import _initialize_interactive_module

_initialize_interactive_module(__name__)
"""


def write_modules() -> None:
    module_contents: collections.defaultdict[Path, list[str]] = collections.defaultdict(
        list
    )

    for module_name in interactive_modules:
        portions = module_name.split(".")
        import_statement = f"from . import {portions[-1]}"
        for i in range(len(portions) - 1):
            parent_name = "/".join(portions[: i + 1])
            parent_path = interactive_path / parent_name / "__init__.py"
            if not import_statement in module_contents[parent_path]:
                module_contents[parent_path].append(import_statement)

        module_path = interactive_path / module_name.replace(".", "/") / "__init__.py"
        module_contents[module_path].append(
            LOWEST_LEVEL_CONTENTS.format(name=portions[-1]).strip()
        )

    for path, contents in module_contents.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(contents))

        black.format_file_in_place(
            path,
            fast=False,
            mode=black.Mode(is_pyi=True),
            write_back=black.WriteBack.YES,
        )
        isort.api.sort_file(path, quiet=True, profile="black")

        print(f"Created {str(path)}")


def write_stubs() -> None:
    for module in interactive_modules:
        module = "rail.interactive." + module
        importlib.import_module(module)
        _initialize_interactive_module(module, write_stubs=True)


if __name__ == "__main__":
    if pytest.main(["tests/interactive"]) != 0:
        sys.exit()
    write_modules()
    write_stubs()
