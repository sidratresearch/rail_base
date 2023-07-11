import os
import numpy as np
import pytest

from rail.core.utils import RAILDIR, find_rail_file
from rail.core.stage import RailStage
from rail.core.data import QPHandle
from rail.estimation.algos.naiveClassifierSRD import naiveClassifierSRD


DS = RailStage.data_store
DS.__class__.allow_overwrite = True

inputdata = os.path.join(RAILDIR, 'rail/examples_data/testdata/output_BPZ_lite.fits')

@pytest.mark.parametrize(
    "input_param", 
    [{"zbin_edges": [0.0, 0.3]},
     {"zmin": 0.0, "zmax": 0.3, "nbins": 1},
     {"zmin": 0.0, "zmax": 0.3, "nbins": 1, "equal_ngal": True},
    ]
)

def test_tomographer(input_param):
    DS.clear()    
    input_data = DS.read_file('input_data', QPHandle, inputdata)

    tomo = naiveClassifierSRD.make_stage(
        point_estimate='zmode',
        **input_param,
    )
    
    out_data = tomo.tomography(input_data)
    
    
