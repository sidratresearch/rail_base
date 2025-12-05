from typing import Any

from ceci.config import StageParameter as Param

from rail.core import RailStage


class AABFakeRailStage(RailStage):
    """A fake RailStage for testing, named to be second alphabetically"""

    name = "AABFakeRailStage"
    entrypoint_function = "maybe_lie"
    interactive_function = "aab_fake_stage"
    inputs = []
    outputs = []
    config_options = RailStage.config_options.copy()
    config_options.update(
        truthiness=Param(float, None, msg="How truthful the output should be"),
    )

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

    def maybe_lie(self, truth: str, **kwargs: Any) -> None:
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
