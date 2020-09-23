# 
#
# Just a simple main method to test during lambda development.
# Can safly ignore this or use for your own development on the edge device 
# with Realsense camera attached. 
#
# Author: Dean Colcott - https://www.linkedin.com/in/deancolcott/
#


import sys
from neural_compute.intel_ncs import IntelNcs as Ncs

def test_intel_ncs():
    """
    Initial test to load Intel NCS code example
    """
    try:
        ncs = Ncs()


    except KeyboardInterrupt:
        print('Exiting.....')
        sys.exit()

    except Exception as e:
        print(repr(e))

if __name__ == "__main__":

    test_intel_ncs()
