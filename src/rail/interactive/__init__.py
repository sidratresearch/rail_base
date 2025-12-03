"""
A "factory" of sorts, turning regular class-based RAIL stages into single-call functions
for interactive use
"""

import types

from .utils import (
    attatch_interactive_namespaces,
    check_interactive_function_names,
    create_attatch_interactive_function,
    get_interactive_namespace_names,
    get_rail_stages,
)

# look through and get all rail stages

rail_stages = get_rail_stages(silent=True)

# look through rail stages and their interactive names
# if names collide, raise error

check_interactive_function_names(rail_stages, silent=True)

# add all sub-namespaces, where the interactive functions will live

namespace_names = get_interactive_namespace_names(rail_stages, silent=True)
namespace_dict = attatch_interactive_namespaces(namespace_names, silent=True)

# for each rail stage make a new function, named after the interactive_function
# class parameter

# for class_name, import_path in rail_stages.items():
#     create_attatch_interactive_function(
#         class_name, import_path, namespace_dict, silent=True
#     )
#     break


def fakefake(**kwargs):
    print(kwargs)


__all__ = ["creation"]
not_creation = types.ModuleType("creation")  # namespace_dict["rail.creation"]
not_creation.__all__ = ["degraders", "pprint"]
not_creation.__name__ = "rail.interactive.creation"  # no apparent effect
not_creation.__package__ = "rail.interactive.creation"  # no apparent effect
not_creation.degraders = types.ModuleType("degraders")
not_creation.pprint = print
setattr(not_creation, "pprint", print)
# setattr(not_creation, "degraders", types.ModuleType("degraders"))
setattr(not_creation.degraders, "addRandom", types.ModuleType("addRandom"))
setattr(not_creation.degraders.addRandom, "aaa_fake_stage", fakefake)
creation = not_creation
creation.pprint = print
setattr(creation, "pprint", print)
# creation.degraders = namespace_dict["rail.creation.degraders"]


def interactive_function(**kwargs):
    """
    RailStage class summary docstring

    entrypoint_function summary docstring

    Some text indicating where to find the source code actually being run

    Parameters
    ---------
    entrypoint_function params (make sure all EPFs have good docstrings)
    RailStage class params (without input/output)
    RailStage class inputs, using docstrings from the type of the handle

    Returns
    -------
    entrypoint_function return (make sure all EPFs have good docstrings)

    any text from ParentRailStage.extra_interactive_documentation (examples)
    """
    print("Hello")
    # interpret the input data, and transform it to whatever type of Handle is needed
    # call make stage and then the entrypoint function, passing all kwargs to both
    # return the output of the entrypoint function


# for each new function, attatch it to the interactive namespace
