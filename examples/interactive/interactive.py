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

sys.exit()

# from rail.interactive.creation.degraders.addRandom import aaa_fake_stage

print(interact.creation.__all__)
print(dir(interact.creation))
from rail.interactive.creation import pprint

pprint("hi")


# import rail.creation.degraders
# from rail.creation import degraders
# from rail.creation import noisifier
# from rail.creation.degraders.addRandom import AAAFakeRailStage
# from rail.estimation import algos

# print(AAAFakeRailStage)
# print(degraders.addRandom)


aaa_fake_stage(truthiness=0, truth="Cow says moo")

# currently broken unless you manually set __all__ in init - rail.interactive has no attribute "creation"
print(interact.creation)
print(interact.creation.degraders.__dict__)
print(interact.creation.degraders)
print(interact.creation.degraders.addRandom)
print(dir(interact.creation.degraders.addRandom))
interact.creation.degraders.addRandom.aaa_fake_stage(
    truthiness=1, truth="Cat says meow"
)
