from typing import Any

def aaa_fake_stage(**kwargs) -> Any:
    """
    A fake RailStage for testing, named to be first alphabetically

    ---

    Main function for FakeRailStage

    Needs to have **kwargs, or else things from __init__ will "overflow" (unexpected
    keyword argument)

    ---

    This function was generated from the function
    rail.creation.degraders.addRandom.AAAFakeRailStage.maybe_lie

    Parameters
    ----------
    truth : str
        The string to print
    output_mode: [str] default=default
        What to do with the outputs
    truthiness: [float] (required)
        How truthful the output should be
    """
