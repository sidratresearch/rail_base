"""
Abstract base classes defining Estimators of individual galaxy redshift uncertainties
"""
import numpy as np
from numpy.typing import NDArray

from rail.core.common_params import SHARED_PARAMS
from rail.core.data import TableHandle, QPHandle, ModelHandle
from rail.core.stage import RailStage

import gc

from rail.estimation.informer import CatInformer
# for backwards compatibility

class CatEstimator(RailStage):
    """The base class for making photo-z posterior estimates from catalog-like inputs
    (i.e., tables with fluxes in photometric bands among the set of columns)

    Estimators use a generic "model", the details of which depends on the sub-class.

    They take as "input" tabular data, apply the photo-z estimation and
    provide as "output" a QPEnsemble, with per-object p(z).

    """

    name = 'CatEstimator'
    config_options = RailStage.config_options.copy()
    config_options.update(
        chunk_size=10000,
        hdf5_groupname=SHARED_PARAMS['hdf5_groupname'],
        calculated_point_estimates=SHARED_PARAMS['calculated_point_estimates'])
    inputs = [('model', ModelHandle),
              ('input', TableHandle)]
    outputs = [('output', QPHandle)]

    def __init__(self, args, comm=None):
        """Initialize Estimator"""
        RailStage.__init__(self, args, comm=comm)
        self._output_handle = None
        self.model = None
        if not isinstance(args, dict):  #pragma: no cover
            args = vars(args)
        self.open_model(**args)

    def open_model(self, **kwargs):
        """Load the mode and/or attach it to this Estimator

        Parameters
        ----------
        model : `object`, `str` or `ModelHandle`
            Either an object with a trained model,
            a path pointing to a file that can be read to obtain the trained model,
            or a `ModelHandle` providing access to the trained model.

        Returns
        -------
        self.model : `object`
            The object encapsulating the trained model.
        """
        model = kwargs.get('model', None)
        if model is None or model == 'None':
            self.model = None
            return self.model
        if isinstance(model, str):
            self.model = self.set_data('model', data=None, path=model)
            self.config['model'] = model
            return self.model
        if isinstance(model, ModelHandle):
            if model.has_path:
                self.config['model'] = model.path
        self.model = self.set_data('model', model)
        return self.model

    def estimate(self, input_data):
        """The main interface method for the photo-z estimation

        This will attach the input_data to this `Estimator`
        (for introspection and provenance tracking).

        Then it will call the run() and finalize() methods, which need to
        be implemented by the sub-classes.

        The run() method will need to register the data that it creates to this Estimator
        by using `self.add_data('output', output_data)`.

        Finally, this will return a QPHandle providing access to that output data.

        Parameters
        ----------
        input_data : `dict` or `ModelHandle`
            Either a dictionary of all input data or a `ModelHandle` providing access to the same

        Returns
        -------
        output: `QPHandle`
            Handle providing access to QP ensemble with output data
        """
        self.set_data('input', input_data)
        self.run()
        self.finalize()
        return self.get_handle('output')

    def run(self):
        iterator = self.input_iterator('input')
        first = True
        self._initialize_run()
        self._output_handle = None
        for s, e, test_data in iterator:
            print(f"Process {self.rank} running estimator on chunk {s} - {e}")
            self._process_chunk(s, e, test_data, first)
            first = False
            # Running garbage collection manually seems to be needed
            # to avoid memory growth for some estimators
            gc.collect()
        self._finalize_run()

    def _initialize_run(self):
        self._output_handle = None

    def _finalize_run(self):
        self._output_handle.finalize_write()

    def _process_chunk(self, start, end, data, first):
        raise NotImplementedError(f"{self.name}._process_chunk is not implemented")  #pragma: no cover

    def _do_chunk_output(self, qp_dstn, start, end, first):
        if first:
            self._output_handle = self.add_handle('output', data = qp_dstn)
            self._output_handle.initialize_write(self._input_length, communicator = self.comm)
        self._output_handle.set_data(qp_dstn, partial=True)
        self._output_handle.write_chunk(start, end)

    def _calculate_point_estimates(self, qp_dist, grid:NDArray=None) -> dict:
        """This function drives the calculation of point estimates for qp.Ensembles.
        It is defined here, and called from the `_process_chunk` method in the
        `CatEstimator` child classes.

        Parameters
        ----------
        qp_dist : qp.Ensemble
            The qp Ensemble instance that contains posterior estimates.
        grid : NDArray, optional
            The grid on which to evaluate the point estimate. Note that not all
            point estimates require a grid to be provided, by default None.

        Returns
        -------
        dict
            The ancillary dictionary that contains the point estimates. The possible
            keys are ['mean', 'mode', 'median'].

        Notes
        -----
        If there are particularly efficient ways to calculate point estimates for
        a given `CatEstimator` subclass, the subclass can implement any of the
        `_calculate_<foo>_point_estimate` for any of the point estimate calculator
        methods, i.e.:

            - `_calculate_mode_point_estimate`
            - `_calculate_mean_point_estimate`
            - `_calculate_median_point_estimate`
        """

        ancil_dict = dict()
        calculated_point_estimates = []
        if 'calculated_point_estimates' in self.config:
            calculated_point_estimates = self.config.calculated_point_estimates

        if 'mode' in calculated_point_estimates:
            mode_value = self._calculate_mode_point_estimate(qp_dist, grid)
            ancil_dict.update(mode = mode_value)

        if 'mean' in calculated_point_estimates:
            mean_value = self._calculate_mean_point_estimate(qp_dist)
            ancil_dict.update(mean = mean_value)

        if 'median' in calculated_point_estimates:
            median_value = self._calculate_median_point_estimate(qp_dist)
            ancil_dict.update(median = median_value)

        return ancil_dict

    def _calculate_mode_point_estimate(self, qp_dist, grid:NDArray=None) -> NDArray:
        """Calculates and returns the mode values for a set of posterior estimates
        in a qp.Ensemble instance.

        Parameters
        ----------
        qp_dist : qp.Ensemble
            The qp Ensemble instance that contains posterior estimates.
        grid : NDArray, optional
            The grid on which to evaluate the `mode` point estimate, if a grid is
            not provided, a default will be created at run time using `zmin`, `zmax`,
            and `nzbins`, by default None

        Returns
        -------
        NDArray
            The mode value for each posterior in the qp.Ensemble
        """
        if grid is None:
            for key in ['zmin', 'zmax', 'nzbins']:
                if key not in self.config:
                    raise KeyError(f"Expected `{key}` to be defined in stage configuration dictionary.")

            grid = np.linspace(self.config.zmin, self.config.zmax, self.config.nzbins)

        return qp_dist.mode(grid=self.zgrid)

    def _calculate_mean_point_estimate(self, qp_dist) -> NDArray:
        """Calculates and returns the mean values for a set of posterior estimates
        in a qp.Ensemble instance.

        Parameters
        ----------
        qp_dist : qp.Ensemble
            The qp Ensemble instance that contains posterior estimates.

        Returns
        -------
        NDArray
            The mean value for each posterior in the qp.Ensemble
        """
        return qp_dist.mean()

    def _calculate_median_point_estimate(self, qp_dist) -> NDArray:
        """Calculates and returns the median values for a set of posterior estimates
        in a qp.Ensemble instance.

        Parameters
        ----------
        qp_dist : qp.Ensemble
            The qp Ensemble instance that contains posterior estimates.

        Returns
        -------
        NDArray
            The median value for each posterior in the qp.Ensemble
        """
        return qp_dist.median()
