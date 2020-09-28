# realsense-advanced.py
#
# Class to interact with the RealSense camera using mostly simple defaults and no image post processing
# Can capture a frame and return as a Realsense frame object and provides distance to a 
# given X,Y pixel value in the frame.  
#
# Author: Dean Colcott - https://www.linkedin.com/in/deancolcott/
#
#

import os
import pyrealsense2 as rs
import numpy as np
import logging
import json
import sys
import cv2

# Config the logger.
log = logging.getLogger(__name__)
logging.basicConfig(format="%(asctime)s - %(name)s - [%(levelname)s] - %(message)s", stream=sys.stdout, level=logging.INFO)


PRESET_CONFIG = "./realsense/preset-configs/DefaultPreset_D435.json"

class RealsenseDevice:
    """
    Interact with the RealSense d4xx camera initialising from library of pre-set configurations with various 
    objectives to optimise density, accuracy, range and resolution.
    """

    def __init__(self):

        log.info('Initialising RealSense Camera')
        # Configure realsense device, 
        self.pipeline = rs.pipeline()
        config = rs.config()
        profile = config.resolve(self.pipeline)

        # Load stream values from predefined config file. 
        log.info('Loading advanced config file: {}'.format(PRESET_CONFIG))
        json_cfg = json.load(open(PRESET_CONFIG))
        # get steram res and FPS vars
        width = int(json_cfg['stream-width'])
        height = int(json_cfg['stream-height'])
        fps = int(json_cfg['stream-fps'])

        log.info('Creating RealSense stream with image width: {}, image height:{} and {} FPS'.format(width, height, fps))

        # Configure depth and color streams (could also add IR stream if desired)
        config.enable_stream(rs.stream.depth, width, height, rs.format.z16, fps)
        config.enable_stream(rs.stream.color, width, height, rs.format.bgr8, fps)

        # Start real sense camera streaming
        cfg = self.pipeline.start(config)

        # Set advanced settings on Realsense Camera
        device = cfg.get_device()
        advnc_mode = rs.rs400_advanced_mode(device)
        str_cfg = str(json_cfg).replace("'", '\"')
        advnc_mode.load_json(str_cfg)

        # Capture the device name and serial No for logging / debugging
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

    def get_post_process_depth_frame(self, depth_frame=None, decimation_magnitude=2.0, spatial_magnitude=2.0, spatial_smooth_alpha=0.5,
                                spatial_smooth_delta=20, temporal_smooth_alpha=0.4, temporal_smooth_delta=20):
        """
        Apply a post-processing to the the depth_frame and return the filtered result.
        If depth_frame not provided, the next avilable depth_frame will be taken from RealSense device.

        Parameters:
        -----------
        depth_frame          : rs.frame()
                            The depth frame to be post-processed
        decimation_magnitude : double
                            The magnitude of the decimation filter
        spatial_magnitude    : double
                            The magnitude of the spatial filter
        spatial_smooth_alpha : double
                            The alpha value for spatial filter based smoothening
        spatial_smooth_delta : double
                            The delta value for spatial filter based smoothening
        temporal_smooth_alpha: double
                            The alpha value for temporal filter based smoothening
        temporal_smooth_delta: double
                            The delta value for temporal filter based smoothening
        Return:
        ----------
        filtered_frame : rs.frame()
                        The post-processed depth frame
        """

        # If frames not provided, get next available depth and color frames.
        if not depth_frame:
            depth_frame = self.get_rbg_depth_frames()['depth_frame']

        # Post processing possible only on the depth_frame
        assert (depth_frame.is_depth_frame())

        # Available filters and control options for the filters
        decimation_filter = rs.decimation_filter()
        spatial_filter = rs.spatial_filter()
        temporal_filter = rs.temporal_filter()

        filter_magnitude = rs.option.filter_magnitude
        filter_smooth_alpha = rs.option.filter_smooth_alpha
        filter_smooth_delta = rs.option.filter_smooth_delta

        # Apply the control parameters for the filter
        decimation_filter.set_option(filter_magnitude, decimation_magnitude)

        spatial_filter.set_option(filter_magnitude, spatial_magnitude)
        spatial_filter.set_option(filter_smooth_alpha, spatial_smooth_alpha)
        spatial_filter.set_option(filter_smooth_delta, spatial_smooth_delta)
        spatial_filter.set_option(rs.option.holes_fill, 3)
        
        temporal_filter.set_option(filter_smooth_alpha, temporal_smooth_alpha)
        temporal_filter.set_option(filter_smooth_delta, temporal_smooth_delta)

        # Apply the filters
        filtered_frame = decimation_filter.process(depth_frame)
        filtered_frame = spatial_filter.process(filtered_frame)
        filtered_frame = temporal_filter.process(filtered_frame)

        return filtered_frame.as_depth_frame()

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
    
    def get_distance_to_frame_pixel(self, depth_frame=None, x=None, y=None):
        """
        Returns the distance measured (in Meters) to the x, y pixel of the depth_frame

        depth_frame: (Optional) The depth_frame to perform the depth measurement on, 
        if not provided will take the next available depth frame from the RealSense Device.

        X / Y: (Optional) Will default to center of the given depth_frame if not provided.
        """

        # If previous depth frames not provided, get next avaliabe frame from realsense.
        if not depth_frame:
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

    