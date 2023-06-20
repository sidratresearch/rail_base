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
    config_options = PZTomographer.config_options.copy()
    config_options.update(
        tomo_config=Param(str, 'tomo_binning.ini', msg="Configuration file for tomographic binning"),
        point_estimate=Param(str, 'zmode', msg="Which point estimate to use"),)
    outputs = [('output', TableHandle)]
    
    def __init__(self, args, comm=None):
        PZTomographer.__init__(self, args, comm=comm)
        
    def read_config(self):
        # read the binning_option:
        param_list=["zmin", "zmax", "nbins", "equal_ngal", "zbin_edges"]
        bin_config={}
        
        lines=open(self.config.tomo_config,'r').readlines() #read all the lines
        nline=len(lines)
        for tmp in lines:
            tsplit=tmp.split()
            if(tmp=='\n' or tmp[0]=='#'):
                continue
            elif(tsplit[0] in param_list and tsplit[1]=='='):
                if tsplit[0] in ["zmin", "zmax"]:
                    bin_config[tsplit[0]]=float(tsplit[2])
                elif tsplit[0] in ["nbins", "equal_ngal"]:
                    bin_config[tsplit[0]]=int(tsplit[2])
                elif tsplit[0] == "zbin_edges":
                    bin_config[tsplit[0]]=[]
                    for jj in range(2,len(tsplit)):
                         bin_config[tsplit[0]].append(float(tsplit[jj]))
           
        return bin_config
    
    def run(self):
        
        # load config:
        bin_config=read_config()
        test_data = self.get_data('input')
        npdf = test_data.npdf
        zb = test_data.ancil[self.config.point_estimate]
        
        # binning options
        if "zbin_edges" in list(bin_config.keys()):
            # this overwrites all other key words
            # linear binning defined by zmin, zmax, and nbins
            bin_index = np.digitize(zb, bin_config["zbin_edges"])
            # assign -99 to objects not in any bin:
            bin_index[bin_index==0]=-99
            bin_index[bin_index==len(bin_config["zbin_edges"])]=-99
        
        else:
            if config["equal_ngal"] == 0:
                # linear binning defined by zmin, zmax, and nbins
                bin_index = np.digitize(zb, np.linspace(bin_config["zmin"], bin_config["zmax"], bin_config["nbins"]+1))
                # assign -99 to objects not in any bin:
                bin_index[bin_index==0]=-99
                bin_index[bin_index==(bin_config["nbins"]+1)]=-99

            elif config["equal_ngal"] == 1:
                # tomographic bins with equal number density
                sortind = np.argsort(zb)
                cum=np.arange(1,(len(zb)+1))
                bin_index = np.zeros(len(zb))
                for ii in range(bin_config["nbins"]):
                    perc1=ii/bin_config["nbins"]
                    perc2=(ii+1)/bin_config["nbins"]
                    ind=(cum/cum[-1]>perc1)&(cum/cum[-1]<=perc2)
                    useind=sortind[ind]
                    bin_index[useind] = int(ii+1)

        tomo = {"tomo": bin_index}
        self.add_data('output', tomo)