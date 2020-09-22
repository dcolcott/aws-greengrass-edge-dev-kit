# realsense-advanced.py
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
import json
import sys
import cv2

# Config the logger.
log = logging.getLogger(__name__)
logging.basicConfig(format="%(asctime)s - %(name)s - [%(levelname)s] - %(message)s", stream=sys.stdout, level=logging.INFO)


PRESET_CONFIG = "../preset-configs/DefaultPreset_D435.json"

class RealsenseDevice:
    """
    Interact with the RealSense d4xx camera initialising with mostly simple defaults and no image post processing
    """

    def __init__(self):

        log.info('Initialising Realsense Camera')
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

        log.info('Creating Realsense stream with image width: {}, image height:{} and {} FPS'.format(width, height, fps))

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
        log.info('{} - Serial:{} Successfully Initialised'.format(self.rs_name, self.rs_serial))

    def get_rbg_depth_frames(self):
        """
        Returns a dict of the latest next color and depth frames from the RealSense Device
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

    def get_post_process_depth_frame(self, depth_frame, decimation_magnitude=2.0, spatial_magnitude=2.0, spatial_smooth_alpha=0.5,
                                spatial_smooth_delta=20, temporal_smooth_alpha=0.4, temporal_smooth_delta=20):
        """
        Filter the depth frame acquired using the Intel RealSense device
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

    def get_frames_as_np_array(self):
        """
        Returns a dict of the latest available color and colorised depth frames from 
        the RealSense Device as an np array
        """

        # Get next avaliabe depth and color frames.
        frames = get_rbg_depth_frames()
        depth_frame = frames['depth-frame']
        color_frame = frames['color-frame']
        filtered_depth_frame = self.get_post_process_depth_frame(depth_frame)

        # Convert images to numpy arrays
        depth_image = np.asanyarray(depth_frame.get_data())
        filtered_depth_image = np.asanyarray(filtered_depth_frame.get_data())
        color_image = np.asanyarray(color_frame.get_data())

        # Apply colormap on depth image
        depth_colormap = np.asanyarray(rs.colorizer().colorize(depth_frame).get_data())
        filtered_depth_colormap = np.asanyarray(rs.colorizer().colorize(filtered_depth_frame).get_data())

        return {'color-image' : color_image, 'depth-colormap' : depth_colormap, 'filtered_depth_colormap' : filtered_depth_colormap}

    def get_resize_frames_as_np_array(self, width, height):

        frames = self.get_frames_as_np_array()
        return {
            'color-image' : cv2.resize(frames['color_image'], (width, height)), 
            'depth-colormap' : cv2.resize(frames['depth_colormap'], (width, height)),
            'filtered_depth_colormap' : cv2.resize(frames['filtered_depth_colormap'], (width, height))
            }

    def get_distance_to_frame_pixel(self, x=None, y=None):
        """
        Returns the distance measured (in Meters) to the x, y pixel of the 
        next available depth frame from the RealSense Device.

        Distance is measured on the post-processed depth frame whch can adjust the frame size. 

        X / Y Optional: Will default to center of the given image plane if is not set.
        """

        depth_frame = self.get_rbg_depth_frames()['depth-frame']
        filtered_frame = self.get_post_process_depth_frame(depth_frame)

        # If not x or y set then set to center of given image plane
        # Set after filter frame is processed as this can change the frame size
        if not x:
            x = int(filtered_frame.get_width() / 2)
        
        if not y:
            y = int(filtered_frame.get_height() / 2)
        
        zDepth = filtered_frame.get_distance(x, y)
        zDepth = '{:.3f}'.format(zDepth)
        return zDepth

    def close_realsense_connection(self):
        self.pipeline.stop()
        log.info('Realsense pipeline successfully closed for {} - Serial {}'.format(self.rs_name, self.rs_serial))

    