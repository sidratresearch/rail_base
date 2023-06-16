"""
Abstract base classes defining redshift estimations Tomographers
"""
from rail.core.data import QPHandle, TableHandle, ModelHandle
from rail.core.stage import RailStage

class CatTomographer(RailStage):
    """The base class for assigning tomographic bins to catalogue-like table.

    Tomographer use a generic "model", the details of which depends on the sub-class.

    CatTomographer take as "input" a catalogue-like table, assign each object into
    a tomographic bin, and provide as "output" a tabular data which can be appended 
    to the catalogue.
    """
    
    name='CatTomograhper'
    config_options = RailStage.config_options.copy()
    config_options.update(chunk_size=10000)
    inputs = [('input', TableHandle)]
    outputs = [('output', TableHandle)]
    
    def __init__(self, args, comm=None):
        """Initialize Summarizer"""
        RailStage.__init__(self, args, comm=comm)
        
    def tomography(self, input_data):
        """The main run method for the tomographer, should be implemented
        in the specific subclass.

        This will attach the input_data to this `CatTomograhper`
        (for introspection and provenance tracking).

        Then it will call the run() and finalize() methods, which need to
        be implemented by the sub-classes.

        The run() method will need to register the data that it creates to this Tomographer
        by using `self.add_data('output', output_data)`.

        Finally, this will return a TableHandle providing access to that output data.

        Parameters
        ----------
        input_data : `dict`
            A dictionary of all input data

        Returns
        -------
        output: `dict`
            Tomographic assignment for each galaxy. No assignment=-99.
        """
        self.set_data('input', input_data)
        self.run()
        self.finalize()
        return self.get_handle('output')
    

class PZTomographer(RailStage):
    """The base class for assigning tomographic bins to per-galaxy PZ estimates

    PZTomographer take as "input" a `qp.Ensemble` with per-galaxy PDFs, and
    provide as "output" a tabular data which can be appended to the catalogue.
    """
    
    name='PZTomograhper'
    config_options = RailStage.config_options.copy()
    config_options.update(chunk_size=10000)
    inputs = [('input', QPHandle)]
    outputs = [('output', TableHandle)]
    
    def __init__(self, args, comm=None):
        """Initialize Summarizer"""
        RailStage.__init__(self, args, comm=comm)
        
    def tomography(self, input_data):
        """The main run method for the tomographer, should be implemented
        in the specific subclass.

        This will attach the input_data to this `PZTomograhper`
        (for introspection and provenance tracking).

        Then it will call the run() and finalize() methods, which need to
        be implemented by the sub-classes.

        The run() method will need to register the data that it creates to this Tomographer
        by using `self.add_data('output', output_data)`.

        Finally, this will return a TableHandle providing access to that output data.

        Parameters
        ----------
        input_data : `qp.Ensemble`
            Per-galaxy p(z), and any ancilary data associated with it

        Returns
        -------
        output: `dict`
            Tomographic assignment for each galaxy. No assignment=-99.
        """
        self.set_data('input', input_data)
        self.run()
        self.finalize()
        return self.get_handle('output')