"""
A classifier that uses pz point estimate to assign
tomographic bins according to SRD
"""

import numpy as np
from ceci.config import StageParameter as Param
from rail.estimation.tomographer import PZTomographer
from rail.core.data import TableHandle

class naiveClassifierSRD(PZTomographer):
    """Classifier that simply assign tomographic
    bins based on point estimate according to SRD"""

    name = 'naiveClassifierSRD'
    config_options = PZTomographer.config_options.copy()
    config_options.update(
        #tomo_config=Param(str, 'tomo_binning.ini', msg="Configuration file for tomographic binning"),
        point_estimate=Param(str, 'zmode', msg="Which point estimate to use"),
        zbin_edges=Param(list, [], msg="The tomographic redshift bin edges. If this is given (contains two or more entries), all settings below will be ignored."),
        zmin=Param(float, 0.0, msg="Minimum redshift of the sample"),
        zmax=Param(float, 3.0, msg="Maximum redshift of the sample"),
        nbins=Param(int, 5, msg="Number of tomographic bins"),
        equal_ngal=Param(bool, False, msg="If equal_ngal=0, creat linear nbins between zmin and zmax; if equal_ngal=1, create nbins between zmin and zmax containing same number of galaxies."),
        )
    outputs = [('output', TableHandle)]

    def __init__(self, args, comm=None):
        PZTomographer.__init__(self, args, comm=comm)

    def run(self):

        # load config:
        #bin_config = self.read_bins()
        test_data = self.get_data('input')
        npdf = test_data.npdf
        zb = test_data.ancil[self.config.point_estimate]

        # binning options
        if len(self.config.zbin_edges)>=2:
            # this overwrites all other key words
            # linear binning defined by zmin, zmax, and nbins
            bin_index = np.digitize(zb, self.config.zbin_edges)
            # assign -99 to objects not in any bin:
            bin_index[bin_index==0]=-99
            bin_index[bin_index==len(self.config.zbin_edges)]=-99

        else:
            if self.config.equal_ngal == 0:
                # linear binning defined by zmin, zmax, and nbins
                bin_index = np.digitize(zb, np.linspace(self.config.zmin, self.config.zmax, self.config.nbins+1))
                # assign -99 to objects not in any bin:
                bin_index[bin_index==0]=-99
                bin_index[bin_index==(self.config.nbins+1)]=-99

            elif self.config.equal_ngal == 1:
                # tomographic bins with equal number density
                sortind = np.argsort(zb)
                cum=np.arange(1,(len(zb)+1))
                bin_index = np.zeros(len(zb))
                for ii in range(self.config.nbins):
                    perc1=ii/self.config.nbins
                    perc2=(ii+1)/self.config.nbins
                    ind=(cum/cum[-1]>perc1)&(cum/cum[-1]<=perc2)
                    useind=sortind[ind]
                    bin_index[useind] = int(ii+1)

        tomo = {"tomo": bin_index}
        self.add_data('output', tomo)
