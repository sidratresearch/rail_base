"""
A classifier that uses pz point estimate to assign
tomographic bins with uniform binning. 
"""

import numpy as np
from ceci.config import StageParameter as Param
from rail.estimation.classifier import PZClassifier
from rail.core.data import TableHandle, Hdf5Handle

class UniformBinningClassifier(PZClassifier):
    """Classifier that simply assign tomographic
    bins based on point estimate according to SRD"""

    name = 'UniformBinningClassifier'
    config_options = PZClassifier.config_options.copy()
    config_options.update(
        id_name=Param(str, "", msg="Column name for the object ID in the input data, if empty the row index is used as the ID."),
        point_estimate=Param(str, 'zmode', msg="Which point estimate to use"),
        zbin_edges=Param(list, [], msg="The tomographic redshift bin edges. If this is given (contains two or more entries), all settings below will be ignored."),
        zmin=Param(float, 0.0, msg="Minimum redshift of the sample"),
        zmax=Param(float, 3.0, msg="Maximum redshift of the sample"),
        nbins=Param(int, 5, msg="Number of tomographic bins"),
        no_assign=Param(int, -99, msg="Value for no assignment flag"),
        )
    outputs = [('output', Hdf5Handle)]
    
    
    def __init__(self, args, comm=None):
        PZClassifier.__init__(self, args, comm=comm)
    

    def _process_chunk(self, s, e, test_data, first):
        try:
            zb = test_data.ancil[self.config.point_estimate]
        except KeyError:
            raise KeyError(f"{self.config.point_estimate} is not contained in the data ancil, you will need to compute it explicitly.")

        # binning options
        if len(self.config.zbin_edges)>=2:
            # this overwrites all other key words
            # linear binning defined by zmin, zmax, and nbins
            bin_index = np.digitize(zb, self.config.zbin_edges)
            # assign -99 to objects not in any bin:
            bin_index[bin_index==0]=self.config.no_assign
            bin_index[bin_index==len(self.config.zbin_edges)]=self.config.no_assign
        else:
            # linear binning defined by zmin, zmax, and nbins
            bin_index = np.digitize(zb, np.linspace(self.config.zmin, self.config.zmax, self.config.nbins+1))
            # assign -99 to objects not in any bin:
            bin_index[bin_index==0]=self.config.no_assign
            bin_index[bin_index==(self.config.nbins+1)]=self.config.no_assign
        
        if self.config.id_name != "":
            # below is commented out and replaced by a redundant line
            # because the data doesn't have ID yet
            # obj_id = test_data[self.config.id_name]
            obj_id = np.arange(test_data.npdf)
        elif self.config.id_name == "":
            # ID set to row index
            obj_id = np.arange(test_data.npdf)
            self.config.id_name="row_index"
        
        class_id = {self.config.id_name: obj_id, "class_id": bin_index}
        self._do_chunk_output(class_id, s, e, first)


    # def _finalize_run(self):
    #     self._output_handle.finalize_write()

    
    # def _do_chunk_output(self, class_id, start, end, first):
    #     if first:
    #         self._output_handle = self.add_handle('output', data=class_id)
    #         self._output_handle.initialize_write(self._input_length, communicator=self.comm)
    #     self._output_handle.set_data(class_id, partial=True)
    #     self._output_handle.write_chunk(start, end)


    # def run(self):
    #     test_data = self.get_data('input')
        
    #     iterator = self.input_iterator('input') # calling RailStage's input_iterator here
    #     first = True
    #     self._output_handle = None
        
    #     for s, e, test_data in iterator:
    #         #print(f"Process {self.rank} running estimator on chunk {s} - {e}")
    #         self._process_chunk(s, e, test_data, first)
    #         first = False
    #         # Running garbage collection manually seems to be needed
    #         # to avoid memory growth for some estimators
    #         gc.collect()
    #     self._finalize_run()
