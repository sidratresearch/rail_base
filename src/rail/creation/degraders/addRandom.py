"""Add a column of random numbers to a dataframe."""

from typing import Any

import numpy as np
from ceci.config import StageParameter as Param

from rail.core import RailStage
from rail.creation.noisifier import Noisifier


class AAAFakeRailStage(RailStage):
    """A fake RailStage for testing, named to be first alphabetically"""

    name = "AAAFakeRailStage"
    entrypoint_function = "maybe_lie"
    interactive_function = "aaa_fake_stage"
    inputs = []
    outputs = []

    def __init__(self, args: Any, **kwargs: Any) -> None:
        super().__init__(args, **kwargs)
        self.truthiness = self.config.truthiness

    def run(self):
        """This stage doesn't need an independent run function.

        Likely the functionality in the entrypoint function could be moved here, but
        self.run() shouldn't take any arguments, so I'm not confident about how to pass
        arbitrary data.

        If we don't add a .run(), pylint throws a warning, and this is considered an
        "incomplete" RAIL stage, so isn't picked up when locating all stages.
        """
        return

    def maybe_lie(self, truth: str, **kwargs) -> None:
        """Main function for FakeRailStage

        Needs to have **kwargs, or else things from __init__ will "overflow" (unexpected
        keyword argument)

        Parameters
        ----------
        truth : str
            The string to print

        Returns
        -------
        None
        """

        if self.truthiness > 0.5:
            print(truth)
        else:
            print(f"NOT {truth}")

        print()


class AddColumnOfRandom(Noisifier):
    """Add a column of random numbers to a dataframe"""

    name = "AddColumnOfRandom"
    entrypoint_function = "__call__"  # the user-facing science function for this class
    config_options = Noisifier.config_options.copy()
    config_options.update(
        col_name=Param(
            str, "chaos_bunny", msg="Name of the column with random numbers"
        ),
    )

    def __init__(self, args: Any, **kwargs: Any) -> None:
        """
        Constructor

        Does standard Noisifier initialization
        """
        Noisifier.__init__(self, args, **kwargs)

    def _initNoiseModel(self) -> None:  # pragma: no cover
        np.random.seed(self.config.seed)

    def _addNoise(self) -> None:  # pragma: no cover
        data = self.get_data("input")
        copy = data.copy()
        copy.insert(0, self.config.col_name, np.random.uniform(size=len(copy)))
        self.add_data("output", copy)
