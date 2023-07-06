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


def test_tomographer():
    DS.clear()    
    input_data = DS.read_file('input_data', QPHandle, inputdata)

    tomo = naiveClassifierSRD.make_stage(
        tomo_config=find_rail_file('examples_data/estimation_data/configs/tomo_binning.ini'),
        point_estimate='zmode'
    )
    
    out_data = tomo.tomography(input_data)
    
    
