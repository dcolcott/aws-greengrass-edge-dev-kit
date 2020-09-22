# realsense-simple.py
#
# Class to interact with the RealSense camera using mostly simple defaults and no image post processing
# Can capture a frame and return as a Realsense frame object and provides distance to a 
# given X,Y pixel value in the frame.  
#
# Author: Dean Colcott - https://www.linkedin.com/in/deancolcott/
#
#
import pyrealsense2 as rs
import numpy as np
import logging
import sys
import cv2

# Config the logger.
log = logging.getLogger(__name__)
logging.basicConfig(format="%(asctime)s - %(name)s - [%(levelname)s] - %(message)s", stream=sys.stdout, level=logging.INFO)

class RealsenseDevice():
    """
    Interact with the RealSense d4xx camera initialising with mostly simple defaults and no image post processing
    """

    def __init__(self):

        log.info('Initialising Realsense Camera')
        # Configure realsense device, 
        self.pipeline = rs.pipeline()
        config = rs.config()
        profile = config.resolve(self.pipeline)

        # Configure depth and color streams (can also add IR stream if desired)
        config.enable_stream(rs.stream.depth, 848, 480, rs.format.z16, 15)
        config.enable_stream(rs.stream.color, 848, 480, rs.format.bgr8, 15)

        # Start real sense camera streaming
        self.pipeline.start(config)

        self.rs_name = profile.get_device().get_info(rs.camera_info.name)
        self.rs_serial = profile.get_device().get_info(rs.camera_info.serial_number)
        log.info('{} - Serial:{} Successfully Initialised'.format(self.rs_name, self.rs_serial))


    def get_rbg_depth_frames(self):
        """
        Returns a dict of the latest available color and depth frames from the RealSense Device
        """

        # Wait for a coherent pair of frames: depth and color
        frames = self.pipeline.wait_for_frames()

        # Create alignment primitive with color as its target stream:
        align = rs.align(rs.stream.color)
        frames = align.process(frames)

        # Capture the depth frame
        depth_frame = frames.get_depth_frame()
        if not depth_frame:
            raise Exception('Depth Frame requested but not available')

        # Capture the Color frame
        color_frame = frames.get_color_frame()
        if not color_frame:
            raise Exception('Color Frame requested but not available')

        return {'color-frame' : color_frame, 'depth-frame' : depth_frame}

    def get_frames_as_np_array(self):
        """
        Returns a dict of the latest available color and colorised depth frames from 
        the RealSense Device as an np array
        """

        # Get next avaliabe depth and color frames.
        frames = self.get_rbg_depth_frames()

        # Convert images to numpy arrays
        depth_image = np.asanyarray(frames['depth-frame'].get_data())
        color_image = np.asanyarray(frames['color-frame'].get_data())

        # Apply colormap on depth image
        depth_colormap = np.asanyarray(rs.colorizer().colorize(depth_frame).get_data())

        return {'color-image' : color_image, 'depth-colormap' : depth_colormap}

    def get_distance_to_frame_pixel(self, x=None, y=None):
        """
        Returns the distance measured (in Meters) to the x, y pixel of the 
        next available depth frame from the RealSense Device.


        X / Y Optional: Will default to center of the given image plane if is not set.
        """
        depth_frame = self.get_rbg_depth_frames()['depth-frame']


        # If not x or y set then set to center of given image plane
        # Set after filter frame is processed as this can change the frame size
        if not x:
            x = int(depth_frame.get_width() / 2)
        
        if not y:
            y = int(depth_frame.get_height() / 2)

        zDepth = depth_frame.get_distance(x, y)
        zDepth = '{:.3f}'.format(zDepth)
        return zDepth

    def close_realsense_connection(self):
        self.pipeline.stop()
        log.info('Realsense pipeline successfully closed for {} - Serial {}'.format(self.rs_name, self.rs_serial))

    