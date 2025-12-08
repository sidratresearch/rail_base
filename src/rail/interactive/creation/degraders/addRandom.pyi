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

def add_column_of_random(**kwargs) -> Any:
    """
    Add a column of random numbers to a dataframe

    ---

    The main interface method for ``Noisifier``.

    Adds noise to the input catalog

    This will attach the input to this `Noisifier`

    Then it will call the _initNoiseModel() and _addNoise(), which need to be
    implemented by the sub-classes.

    The _initNoiseModel() method will initialize the noise model of the sub-classes, and
    store the noise model as self.noiseModel

    The _addNoise() method will add noise to the flux and magnitude of the column of the
    catalog.

    The finalize() method will check the end results (like preserving number of rows)

    Finally, this will return a PqHandle providing access to that output
    data.

    ---

    This function was generated from the function
    rail.creation.degraders.addRandom.AddColumnOfRandom.__call__

    Parameters
    ----------
    sample :
        The sample to be degraded
    seed :
        An integer to set the numpy random seed
    output_mode: [str] default=default
        What to do with the outputs
    seed: [type not specified] default=None
        Set to an `int` to force reproducible results.
    col_name: [str] default=chaos_bunny
        Name of the column with random numbers
    input: PqHandle (INPUT)
    output: PqHandle (OUTPUT)

    Returns
    -------
    output_data : PqHandle
        A handle giving access to a table with degraded sample
    """
