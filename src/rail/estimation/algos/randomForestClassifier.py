"""
An example classifier that uses catalogue information to
classify objects into tomoragphic bins using random forest.
This is the base method in TXPipe, adapted from TXpipe/binning/random_forest.py
Note: extra dependence on sklearn and input training file.
"""

import numpy as np
from ceci.config import StageParameter as Param
from rail.estimation.tomographer import CatTomographer
from rail.core.data import TanbleHandle
from sklearn.ensemble import RandomForestClassifier
import tables_io

class randomForestClassifier(CatTomographer):
    """Classifier that assigns tomographic 
    bins based on random forest method"""
    
    name = 'randomForestClassifier'
    config_options = CatSummarizer.config_options.copy()
    config_options.update(
        bands=Param(tuple, ["g","r","z"], msg="Which bands to use for classification"),
        band_names=param(dict, {}, msg="Band column names"),
        z_name=param(str, "sz", msg="Redshift column names"),
        traning_file=Param(str, '', msg="Training file to use"),
        bin_edges=Param(tuple, [0,0.5,1.0], msg="Binning for training data"),
        random_seed=Param(int, msg="random seed"),)
    outputs = [('output', TableHandle)]
    
    def __init__(self, args, comm=None):
        PZTomographer.__init__(self, args, comm=comm)
            
    def build_tomographic_classifier(self):
        # Load the training data
        training_data_table = tables_io.read(self.config.training_file)

        # Pull out the appropriate columns and combinations of the data
        print(f"Using these bands to train the tomography selector: {self.config.bands}")
        
        # Generate the training data that we will use
        # We record both the name of the column and the data itself
        features = []
        training_data = []
        for b1 in self.config.bands[:]:
            b1_cat=self.config.band_names[b1]
            # First we use the magnitudes themselves
            features.append(b1)
            training_data.append(training_data_table[b1_cat])
            # We also use the colours as training data, even the redundant ones
            for b2 in self.config.bands[:]:
                b2_cat=self.config.band_names[b2]
                if b1 < b2:
                    features.append(f"{b1}-{b2}")
                    training_data.append(training_data_table[b1_cat] - training_data_table[b2_cat])
        training_data = np.array(training_data).T

        print("Training data for bin classifier has shape ", training_data.shape)

        # Now put the training data into redshift bins
        # We use -1 to indicate that we are outside the desired ranges
        z = training_data_table[self.config.z_name]
        training_bin = np.repeat(-1, len(z))
        print("Using these bin edges:", self.config.bin_edges)
        for i, zmin in enumerate(self.config.bin_edges[:-1]):
            zmax = self.config.bin_edges[i + 1]
            training_bin[(z > zmin) & (z < zmax)] = i
            ntrain_bin = ((z > zmin) & (z < zmax)).sum()
            print(f"Training set: {ntrain_bin} objects in tomographic bin {i}")

        # Can be replaced with any classifier
        classifier = RandomForestClassifier(
            max_depth=10,
            max_features=None,
            n_estimators=20,
            random_state=self.config.random_seed,
        )
        classifier.fit(training_data, training_bin)

        return classifier, features

    
    def apply_classifier(self, test_data, classifier, features):
        """Apply the classifier to the measured magnitudes"""

        data = []
        for f in features:
            # may be a single band
            if len(f) == 1:
                f_cat=self.config.band_names[f]
                col = test_data[f_cat]
            # or a colour
            else:
                b1, b2 = f.split("-")
                b1_cat=self.config.band_names[b1]
                b2_cat=self.config.band_names[b2]
                col = (test_data[b1_cat] - test_data[b2_cat])
            if np.all(~np.isfinite(col)):
                # entire column is NaN.  Hopefully this will get deselected elsewhere
                col[:] = 30.0
            else:
                ok = np.isfinite(col)
                col[~ok] = col[ok].max()
            data.append(col)
            data = np.array(data).T

        # Run the random forest on this data chunk
        bin_index = classifier.predict(data)
        return bin_index
        
        
    def run(self):
        """Run random forest classifier"""
        
        test_data = self.get_data('input')
        classifier, features = build_tomographic_classifier()
        bin_index=apply_classifier(test_data, classifier, features)
        tomo = {"tomo": bin_index}
        self.add_data('output', tomo)