#!/usr/bin/env python3

"""
What the final use case should look like:

from rail.interactive.estimators.random_gauss import estimate_random_gauss
estimate_random_gauss(config1=1, data=[0], estimation_config_a="Yes")

OR

from rail import interactive
interactive.estimators.random_gauss.estimate_random_gauss(config1=1, data=[0], estimation_config_a="Yes")
"""

from rail import interactive as interact
from rail.interactive.creation.degraders.addRandom import aaa_fake_stage

print(aaa_fake_stage.__doc__)
aaa_fake_stage(truthiness=0, truth="Cow says moo")

# currently broken - rail.interactive has no attribute "creation"
# interact.creation.degraders.addRandom.aaa_fake_stage(
#     truthiness=1, truth="Cat says meow"
# )
