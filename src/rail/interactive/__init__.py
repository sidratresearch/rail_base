"""
A "factory" of sorts, turning regular class-based RAIL stages into single-call functions
for interactive use
"""

# look through and get all rail stages


# look through rail stages and their interactive names
# if names collide, raise error

# add all sub-namespaces, where the interactive functions will live

# for each rail stage make a new function, named after the interactive_function
# class parameter


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
    # call make stage and then the entrypoint function, passing all kwargs to both
    # return the output of the entrypoint function


# for each new function, attatch it to the interactive namespace
