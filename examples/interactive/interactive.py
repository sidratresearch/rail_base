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

from rail import interactive as interact
from rail.interactive.creation import degraders

degraders.addRandom.aaa_fake_stage(truthiness=1, truth="Rail is interactive")

interact.creation.degraders.addRandom.aaa_fake_stage(truthiness=0, truth="Cow says moo")

sys.exit()
