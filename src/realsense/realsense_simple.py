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

        log.info('Initialising RealSense Camera')
        # Configure RealSense device, 
        self.pipeline = rs.pipeline()
        config = rs.config()
        profile = config.resolve(self.pipeline)

        # Configure depth and color streams (can also add IR stream if desired)
        config.enable_stream(rs.stream.depth, 848, 480, rs.format.z16, 15)
        config.enable_stream(rs.stream.color, 848, 480, rs.format.bgr8, 15)

        # Start RealSense camera streaming
        self.pipeline.start(config)

        self.rs_name = profile.get_device().get_info(rs.camera_info.name)
        self.rs_serial = profile.get_device().get_info(rs.camera_info.serial_number)
        log.info('Successfully Initialised {} - Serial:{}'.format(self.rs_name, self.rs_serial))

    def get_device_name(self):
        return self.rs_name

    def get_device_serial(self):
        return self.rs_serial

    def get_rbg_depth_frames(self):
        """
        Returns a dict of the latest available color and depth frames from the RealSense Device
        labelled as color_frame and depth_frame respectively.
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

        return {'color_frame' : color_frame, 'depth_frame' : depth_frame}

    def get_frames_as_np_array(self, frames=None):
        """
        Takes frames as a dict and converts each to a NP array and returns in a dict with same key values 
        appended with '_np. If a frame is a Realsense Depth frame, a colorised depth map is created and returned for it. 

        frames: (Optional) A dict of named Realsense device frames. If not provided, will take the 
        next available color and depth frame from the RealSense Device and return these 
        labelled as color_frame_np and depth_frame_np respectively.
        """

        # If frames not provided, get next available depth and color frames.
        if not frames:
            frames = self.get_rbg_depth_frames()

        # Convert frames to numpy arrays
        np_arrays = {} 
        for key in frames:
            frame = frames[key]
            if frame.is_depth_frame():
                np_arrays[key + "_np"] =  np.asanyarray(rs.colorizer().colorize(frame).get_data())
            else:
                np_arrays[key + "_np"] = np.asanyarray(frame.get_data())
        
        return np_arrays

    def get_distance_to_frame_pixel(self, depth_frame=None, x=None, y=None):
        """
        Returns the distance measured (in Meters) to the x, y pixel of the depth_frame

        depth_frame: (Optional) The depth_frame to perform the depth measurement on, 
        if not provided will take the next available depth frame from the RealSense Device.

        X / Y: (Optional) Will default to center of the given depth_frame plane if not provided.
        """

        # If previous depth frames not provided, get next available frame from RealSense Device.
        if not depth_frame:
            depth_frame = self.get_rbg_depth_frames()[' depth_frame']

        # If not x or y set then set to center of given image plane
        if not x:
            x = int(depth_frame.get_width() / 2)
        
        if not y:
            y = int(depth_frame.get_height() / 2)

        zDepth = depth_frame.get_distance(x, y)
        zDepth = '{:.3f}'.format(zDepth)
        return zDepth

    def get_resize_np_array(self, width, height, frames=None):
        """
        Computer Vision ML models need to perform inference on images of the same size 
        that they were trained on. This is a simple conveyance function to resize a dict of frames 
        in NP array format to the given width and height. 

        Note: This is a basic example that will introduce distortion to the image if a different aspect than 
        its being resized to. For best results consider more advanced solutions. 

        frames: (Optional) A dict of named RealSense device frames in NP array format. If not provided, will take the 
        next availiable color and depth frame from the RealSense Device and will resize to the given dimentions
        and return these labelled as color_frame_np_resized and depth_frame_np_resized respectively.

        Else will return dict with same keys appended with '_resized'
        """

        # If frames not provided, get next available depth and color frames.
        if not frames:
            frames_np = self.get_frames_as_np_array()

        # Convert frames to numpy arrays
        np_arrays = {}
        for key in frames:
            frame = frames[key]
            if frame.is_depth_frame():
                np_arrays[key + "_resized"] =  np.asanyarray(rs.colorizer().colorize(frame).get_data())
            else:
                np_arrays[key + "_resized"] = np.asanyarray(frame.get_data())
        
        return np_arrays
    
    def close_realsense_connection(self):
        self.pipeline.stop()
        log.info('RealSense pipeline successfully closed for {} - Serial {}'.format(self.rs_name, self.rs_serial))

    