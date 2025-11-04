"""
Example code that just spits out random numbers between 0 and 3
for z_mode, and Gaussian centered at z_mode with width
random_width*(1+zmode).
"""

from typing import Any

import numpy as np
import qp
from ceci.config import StageParameter as Param
from scipy.stats import norm

from rail.core.data import ModelHandle, TableHandle, TableLike
from rail.estimation.estimator import CatEstimator
from rail.estimation.informer import CatInformer


class RandomGaussInformer(CatInformer):
    """Placeholder Informer"""

    name = "RandomGaussInformer"
    config_options = CatInformer.config_options.copy()

    def run(self) -> None:
        self.add_data("model", np.array([None]))


class RandomGaussEstimator(CatEstimator):
    """Random CatEstimator"""

    name = "RandomGaussEstimator"
    inputs = [("input", TableHandle), ("model", ModelHandle)]
    config_options = CatEstimator.config_options.copy()
    config_options.update(
        rand_width=Param(float, 0.025, "ad hock width of PDF"),
        rand_zmin=Param(float, 0.0, msg="The minimum redshift of the z grid"),
        rand_zmax=Param(float, 3.0, msg="The maximum redshift of the z grid"),
        nzbins=Param(int, 301, msg="The number of gridpoints in the z grid"),
        seed=Param(int, 87, msg="random seed"),
        column_name=Param(
            str,
            "mag_i_lsst",
            msg="name of a column that has the "
            "correct number of galaxies to find length of",
        ),
    )

    def __init__(self, args: Any, **kwargs: Any) -> None:
        """Constructor:
        Do CatEstimator specific initialization"""
        super().__init__(args, **kwargs)
        self.zgrid = None

    def core(
        self,
        data: TableLike,
        random_seed: int,
        start: int,
        end: int,
        column_name: str,
        rand_width: float,
        rand_zmax: float,
        rand_zmin: float,
        nzbins: int,
        **kwargs,
    ):
        pdf = []
        # allow for either format for now
        numzs = len(data[column_name])
        rng = np.random.default_rng(seed=random_seed)
        zmode = np.round(rng.uniform(0.0, rand_zmax, numzs), 3)
        widths = rand_width * (1.0 + zmode)
        zgrid = np.linspace(rand_zmin, rand_zmax, nzbins)
        for i in range(numzs):
            pdf.append(norm.pdf(zgrid, zmode[i], widths[i]))
        qp_d = qp.Ensemble(
            qp.stats.norm,  # pylint: disable=no-member
            data=dict(
                loc=np.expand_dims(zmode, -1),  # pylint: disable=no-member
                scale=np.expand_dims(widths, -1),
            ),
        )
        qp_d.set_ancil(dict(zmode=zmode))

        self._update_ancil(qp_d, start, end, data)
        return qp_d, zgrid

    def _process_chunk(
        self, start: int, end: int, data: TableLike, first: bool
    ) -> None:

        # set random seed
        random_seed = self.config.seed + start

        # run the main functionality
        # note - could also pass the whole set of parameters as a dictionary to the function
        # to make this part easier within functions (or as an unpacked dictionary and add kwargs to core)
        qp_d, zgrid = self.core(data, random_seed, start, end, **self.config)

        self.zgrid = zgrid  # do we need to do this?

        # do file IO and adding to DataStore
        self._handle_chunk_output(qp_d, start, end, first, data=data)

    # def _process_chunk(
    #     self, start: int, end: int, data: TableLike, first: bool
    # ) -> None:
    #     pdf = []
    #     # allow for either format for now
    #     numzs = len(data[self.config.column_name])
    #     rng = np.random.default_rng(seed=self.config.seed + start)
    #     zmode = np.round(rng.uniform(0.0, self.config.rand_zmax, numzs), 3)
    #     widths = self.config.rand_width * (1.0 + zmode)
    #     self.zgrid = np.linspace(
    #         self.config.rand_zmin, self.config.rand_zmax, self.config.nzbins
    #     )
    #     for i in range(numzs):
    #         pdf.append(norm.pdf(self.zgrid, zmode[i], widths[i]))
    #     qp_d = qp.Ensemble(
    #         qp.stats.norm,  # pylint: disable=no-member
    #         data=dict(
    #             loc=np.expand_dims(zmode, -1),  # pylint: disable=no-member
    #             scale=np.expand_dims(widths, -1),
    #         ),
    #     )
    #     qp_d.set_ancil(dict(zmode=zmode))
    #     self._do_chunk_output(qp_d, start, end, first, data=data)

    def validate(self) -> None:
        """Validation which checks if the required column names by the stage exist in the data"""
        self._get_stage_columns()
        data = self.get_handle("input", allow_missing=True)
        # **kwargs in the function below is omitted
        # as these params are not yet implemented
        self._check_column_names(data, self.stage_columns)

    def _get_stage_columns(self) -> None:
        self.stage_columns = [self.config.column_name]
