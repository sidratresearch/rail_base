#!/usr/bin/env python3

"""
What the final use case should look like:

from rail.interactive.estimators.random_gauss import estimate_random_gauss
estimate_random_gauss(config1=1, data=[0], estimation_config_a="Yes")

OR

from rail import interactive
interactive.estimators.random_gauss.estimate_random_gauss(config1=1, data=[0], estimation_config_a="Yes")
"""

import sys

import numpy as np
import pandas as pd
import tables_io

from rail import interactive as interact
from rail.interactive.creation import degraders
from rail.interactive.estimation import algos

informer_data = tables_io.read(
    "src/rail/examples_data/testdata/test_dc2_training_9816.hdf5"
)
estimator_data = tables_io.read(
    "src/rail/examples_data/testdata/test_dc2_validation_9816.hdf5"
)

informer_result = algos.random_gauss.random_gauss_informer(
    input=informer_data
)  # makes model.pkl
print("\n\nInformer Result:", informer_result["model"])

estimator_result = algos.random_gauss.random_gauss_estimator(
    input=estimator_data, model=informer_result
)  # makes output.hdf5
print("\n\nEstimator Result:", estimator_result["output"])

# classifier_result = algos.equal_count.equal_count_classifier(
#     input=estimator_result["output"], output_mode="return"
# )

# data = np.random.normal(24, 3, size=(1000, 13))
# data[:, 0] = np.random.uniform(low=0, high=0.03, size=1000)
# data[:, 1] = np.random.uniform(low=0, high=0.03, size=1000)
# data[:, 2] = np.random.uniform(low=0, high=2, size=1000)

# data_df = pd.DataFrame(
#     data=data,  # values
#     columns=["ra", "dec", "z_true", "u", "g", "r", "i", "z", "y", "Y", "J", "H", "F"],
# )
# interactive_result = degraders.addRandom.add_column_of_random(
#     input=data_df
# )  # creates output.pq
# print("\n\nDegrader Result:",interactive_result["output"])


evaluator_output = interact.evaluation.dist_to_point_evaluator.dist_to_point_evaluator(
    input={"data": {"photometry": estimator_result["output"]}, "truth": estimator_data},
)
