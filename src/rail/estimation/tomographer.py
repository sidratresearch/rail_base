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
    config_options.update(chunk_size=10000, hdf5_groupname=str)
    inputs = [('model', ModelHandle),
              ('input', TableHandle)]
    outputs = [('output', TableHandle)]
    
    def __init__(self, args, comm=None):
        """Initialize Summarizer"""
        RailStage.__init__(self, args, comm=comm)
        self._output_handle = None
        self.model = None
        if not isinstance(args, dict):  #pragma: no cover
            args = vars(args)
        self.open_model(**args)
        
    
    def open_model(self, **kwargs):
        """Load the model and/or attach it to this Tomographer

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
    

class CatInformer(RailStage):
    """The base class for informing models used to classify objects into tomographic bins
    from catalog-like inputs (i.e., tables with fluxes in photometric bands among
    the set of columns).

    Tomographers use a generic "model", the details of which depends on the sub-class.
    Most tomographers will have associated Informer classes, which can be used to inform
    those models.

    (Note, "Inform" is more generic than "Train" as it also applies to algorithms that
    are template-based rather than machine learning-based.)

    Informer will produce as output a generic "model", the details of which depends on the sub-class.

    They take as "input" catalog-like tabular data, which is used to "inform" the model.
    """
    name = 'Informer'
    config_options = RailStage.config_options.copy()
    config_options.update(save_train=True, hdf5_groupname=str)
    inputs = [('input', TableHandle)]
    outputs = [('model', ModelHandle)]
    
    def __init__(self, args, comm=None):
        """Initialize Informer that can inform models for classification"""
        RailStage.__init__(self, args, comm=comm)
        self.model = None
    
    
    def inform(self, training_data):
        """The main interface method for Informers

        This will attach the input_data to this `Informer`
        (for introspection and provenance tracking).

        Then it will call the run() and finalize() methods, which need to
        be implemented by the sub-classes.

        The run() method will need to register the model that it creates to this Estimator
        by using `self.add_data('model', model)`.

        Finally, this will return a ModelHandle providing access to the trained model.

        Parameters
        ----------
        input_data : `dict` or `TableHandle`
            dictionary of all input data, or a `TableHandle` providing access to it

        Returns
        -------
        model : ModelHandle
            Handle providing access to trained model
        """
        self.set_data('input', training_data)
        self.run()
        self.finalize()
        return self.get_handle('model')
    
    
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