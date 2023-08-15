import pytest
import numpy as np
from numpy.typing import NDArray
from rail.estimation.estimator import CatEstimator


def test_custom_point_estimate():
    """This test checks to make sure that the inheritance mechanism is working
    for child classes of `CatEstimator`.
    """

    MEANING_OF_LIFE = 42.0
    class TestEstimator(CatEstimator):
        name="TestEstimator"

        def __init__(self, args, comm=None):
            CatEstimator.__init__(self, args, comm=comm)

        def _calculate_mode_point_estimate(self, qp_dist=None, grid=None):
            return np.ones(5) * MEANING_OF_LIFE

    config_dict = {'calculated_point_estimates': ['mode']}

    test_estimator = TestEstimator.make_stage(name='test', **config_dict)

    result = test_estimator._calculate_point_estimates(None, None)

    assert np.all(result['mode'] == MEANING_OF_LIFE)

def test_mode_no_grid():
    """This exercises the KeyError logic in `_calculate_mode_point_estimate`.
    """
    config_dict = {'zmin':0.0, 'nzbins':100, 'calculated_point_estimates': ['mode']}

    test_estimator = CatEstimator.make_stage(name='test', **config_dict)

    with pytest.raises(KeyError) as excinfo:
        _ = test_estimator._calculate_point_estimates(None, None)

    assert "to be defined in stage configuration" in str(excinfo.value)