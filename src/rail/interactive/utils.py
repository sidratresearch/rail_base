"""
Utility functions for the interactive session
"""

# pylint: disable=missing-function-docstring

import functools
import sys
import types
from collections.abc import Callable

import rail
from rail.core import RailEnv
from rail.core.stage import RailStage


def get_rail_stages(silent: bool = False) -> dict[str, str]:
    # pylint: disable=protected-access

    # look through and get all rail stages
    RailEnv.import_all_packages(silent=True)
    RailEnv.attach_stages(rail.stages)

    # modified version of RailEnv.print_rail_stage_dict()
    rail_stages = {}
    for val in RailEnv._stage_dict.values():
        for single_stage in val:
            stage_class = RailStage.pipeline_stages[single_stage][0]
            if stage_class.__name__ not in RailEnv._base_stages_names:
                rail_stages[single_stage] = stage_class.__module__
    rail_stages = dict(sorted(rail_stages.items()))

    if not silent:
        for single_stage, import_path in rail_stages.items():
            print(single_stage, import_path)
        print()

    return rail_stages


if __name__ == "__main__":
    get_rail_stages()


def check_interactive_function_names(rail_stages: dict[str, str], silent=False):
    if not silent:
        print("Checking interactive function names is not implemented")


def get_interactive_namespace_names(
    rail_stages: dict[str, str], silent: bool = False
) -> list[str]:
    needed_namespaces: list[str] = list(set(rail_stages.values()))
    ordered_namespaces: list[str] = []
    for ns in needed_namespaces:
        for i in range(1, ns.count(".") + 1):
            sub_namespace = ".".join(ns.split(".")[: i + 1])
            if sub_namespace not in ordered_namespaces:
                ordered_namespaces.append(sub_namespace)
    return ordered_namespaces


def attatch_interactive_namespaces(
    namespace_names: list[str], silent: bool = False
) -> dict[str, types.ModuleType]:
    namespace_dict: dict[str, types.ModuleType] = {}

    for ns in namespace_names:
        namespace_name = ns.replace("rail.", "rail.interactive.")
        namespace = types.ModuleType(namespace_name)
        setattr(namespace, "__all__", [])
        # namespace.__all__ = []
        # namespace = importlib.util.module_from_spec(
        #     importlib.machinery.ModuleSpec(
        #         name=ns.replace(
        #             "rail.",
        #             "rail.interactive.",
        #         ),
        #         # loader=importlib.machinery.NamespaceLoader,
        #         loader=__spec__.loader,
        #     )
        # )

        namespace_dict[ns] = namespace
        parent_module_name = ns[: ns.rindex(".")]
        if parent_module_name in namespace_dict:
            submodule_name = ns.split(".")[-1]
            namespace_dict[parent_module_name].__all__.append(submodule_name)
            setattr(namespace_dict[parent_module_name], submodule_name, namespace)

        #     print("Adding sub-module")
        #     namespace_dict[parent_module_name].__path__ = __path__[0] + ".py"
        #     setattr(
        #         namespace_dict[parent_module_name], ns[ns.rindex(".") + 1 :], namespace
        #     )
        #     print(dir(namespace_dict[parent_module_name]))

        # namespace.__path__ = []
        # sys.modules[ns.replace("rail.", "rail.interactive.", count=1)] = namespace

        # setattr doesn't work for some reason...
        # gives no module named rail.interactive.X found
        # setattr(
        #     sys.modules[__name__],
        #     ns.replace("rail.", "", count=1),
        #     namespace,
        # )

        if not silent:
            print("Added namespace", ns.replace("rail.", "rail.interactive.", count=1))

    for ns in namespace_names:
        sys.modules[ns.replace("rail.", "rail.interactive.", count=1)] = namespace_dict[
            ns
        ]

    return namespace_dict


def split_docstring_on_title(
    docstring: str, header: str = "Parameters"
) -> tuple[str, str]:
    splitter = header + "\n" + "-" * len(header) + "\n"
    try:
        index = docstring.index(splitter)
        before = docstring[:index].strip()
        after = docstring[index + len(splitter) :].strip()
        return (before, after)

    except ValueError as error:
        raise ValueError("Docstring not well formed") from error


def get_interactive_docstring(rail_stage: RailStage, silent: bool = False) -> str:

    class_docstring = rail_stage.__doc__
    function_docstring = getattr(rail_stage, rail_stage.entrypoint_function).__doc__

    class_summary, class_parameters = split_docstring_on_title(class_docstring)
    function_summary, function_remainder = split_docstring_on_title(function_docstring)
    function_parameters, function_return = split_docstring_on_title(
        function_remainder, "Returns"
    )

    interactive_docstring = f"""
\033[35m{class_summary}\033[0m

\033[32m{function_summary}\033[0m

Parameters
----------
\033[33m{function_parameters}\033[0m
\033[36m{class_parameters}\033[0m

Returns
-------
\033[33m{function_return}\033[0m
    """

    if rail_stage.extra_interactive_documentation is not None:
        interactive_docstring += rail_stage.extra_interactive_documentation

    if not silent:
        print(interactive_docstring)
    return interactive_docstring


def interactive_factory(rail_stage: RailStage, **kwargs) -> Callable:
    instance = rail_stage.make_stage(**kwargs)
    entrypoint_function_name = instance.entrypoint_function
    entrypoint_function: Callable = getattr(instance, entrypoint_function_name)
    return entrypoint_function(**kwargs)


def create_attatch_interactive_function(
    class_name: str,
    noninteractive_import_path: str,
    namespace_dict: dict[str, types.ModuleType],
    silent=False,
) -> None:
    class_definition = RailStage.pipeline_stages[class_name][0]
    function_name = getattr(class_definition, "interactive_function")
    created_function: Callable = functools.partial(
        interactive_factory, class_definition
    )
    created_function.__doc__ = get_interactive_docstring(
        class_definition, silent=silent
    )
    created_function.__module__ = noninteractive_import_path.replace(
        "rail.", "rail.interactive.", count=1
    )
    setattr(
        namespace_dict[noninteractive_import_path],
        function_name,
        created_function,
    )
    if not silent:
        print(
            f"Added function {noninteractive_import_path}.{function_name} created from {class_name}"
        )
