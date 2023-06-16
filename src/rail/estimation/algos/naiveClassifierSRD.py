"""
A classifier that uses pz point estimate to assign
tomographic bins according to SRD
"""

import numpy as np
from ceci.config import StageParameter as Param
from rail.estimation.tomographer import PZTomographer
from rail.core.data import TanbleHandle

class naiveClassifierSRD(PZTomographer):
    """Classifier that simply assign tomographic 
    bins based on point estimate according to SRD"""
    
    name = 'naiveClassifierSRD'
    config_options = PZSummarizer.config_options.copy()
    config_options.update(
        binning_option=Param(str, 'lensY1', msg="Which binning in SRD to use (lensY1, lensY10, source)",
        point_estimate=Param(str, 'zmode', msg="Which point estimate to use"))
    outputs = [('output', TableHandle)]
    
    def __init__(self, args, comm=None):
        PZTomographer.__init__(self, args, comm=comm)
        
    def run(self):
        test_data = self.get_data('input')
        npdf = test_data.npdf
        zb = test_data.ancil[self.config.point_estimate]
        
        # binning option
        if self.config.binning_option == 'lensY1':
            # 5 bins between 0.2<z<1.2
            bin_index = np.digitize(zb, np.linspace(0.2,1.2,6))
            # assign -99 to objects not in any bin:
            bin_index[bin_index==0]=-99
            bin_index[bin_index==6]=-99
    
        elif self.config.binning_option == 'lensY10':
            # 10 bins between 0.2<z<1.2
            bin_index = np.digitize(pz, np.linspace(0.2,1.2,11))
            bin_index[bin_index==0]=-99
            bin_index[bin_index==11]=-99

        elif self.config.binning_option == 'source':
            # 5 bins with equal number density
            sortind = np.argsort(zb)
            N_perbin = int(len(bz)/nbins)
            bin_index = np.zeros(len(zb))
            for ii in range(nbins):
                useind = sortind[ii*N_perbin:(ii+1)*N_perbin]
                bin_index[useind] = int(ii+1)

        tomo = {"tomo": bin_index}
        self.add_data('output', tomo)