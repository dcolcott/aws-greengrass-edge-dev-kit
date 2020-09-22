# 
#
# Just a simple main method to test during lambda development.
# Can safly ignore this or use for your own development on the edge device 
# with Realsense camera attached. 
#
# Author: Dean Colcott - https://www.linkedin.com/in/deancolcott/
#


import sys
from realsense.realsense_simple import RealsenseDevice as RealsenseSimple


def test_distance_simple(x, y):
    """
    Prints the distance to X, Y in frame from realsense-simple example
    """
    try:
        rs_simple = RealsenseSimple()

        while(True):
            zDepth = rs_simple.get_distance_to_frame_pixel(x, y)
            print('REALSENSE-SIMPLE: Distance in frame at x: {}, y:{} is: {}'.format(x, y, zDepth))  

    except KeyboardInterrupt:
        print('Exiting.....')
        sys.exit()

    except Exception as e:
        print(repr(e))
    
    finally:
        rs_simple.close_realsense_connection()

if __name__ == "__main__":

    x = 440
    y = 220
    test_distance_simple(x, y)
