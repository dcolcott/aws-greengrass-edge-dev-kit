# realsense-advanced.py
#
# Takes colour and depth image from the Intel RelSense 3D camera
# Detects the distance to the center of the image frame and logs to SysOut. 
# Apply's Realsense RS400 advanced settings form pre-configured visual presets
#
# Author: Dean Colcott - https://www.linkedin.com/in/deancolcott/
#
# Credits: Examples from  https://github.com/IntelRealSense/librealsense
# Visual presets based on: https://github.com/IntelRealSense/librealsense/wiki/D400-Series-Visual-Presets
#
#
import pyrealsense2 as rs
import numpy as np
import logging as log
import time
import sys
import json
import cv2

# Config the logger.
log.basicConfig(format="[ %(levelname)s ] %(message)s", level=log.INFO, stream=sys.stdout)

PRESET_CONFIG = "./preset-configs/HighResHighDensityPreset.json"

# Image file save location.
DEPTH_IMAGE_PATH = '/home/pi/Desktop/depth_image.jpg'
DEPTH_COLORMAP_PATH= '/home/pi/Desktop/depth_colormap.jpg'
PROCESSED_DEPTH_COLORMAP_PATH = '/home/pi/Desktop/processed_depth_colormap.jpg'
COLOR_IMAGE_PATH = '/home/pi/Desktop/color_image.jpg'

class RealsenseDevice():
    """
    Captured a RGB and Depth image from the Realsense D453i camera and saves to a local file.
    """
    def __init__(self):

        log.info('Initialising Realsense Camera')
        # Configure realsense device, 
        self.pipeline = rs.pipeline()
        config = rs.config()
        profile = config.resolve(self.pipeline)

        # Load stream values from predefined config file. 
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


    def capture_image(self, resize_width, resize_height):

        try:
            # Skip 5 first frames to give the Auto-Exposure time to adjust
            log.info('Captured realsense image - waiting for auto-exposure to adjust')
            for x in range(5):
               self.pipeline.wait_for_frames()
               log.info('Captured wait frame: {}'.format(x))

            log.info('Starting depth image processing, press Ctl-C to exit.')
            while(True):
                try:
                    # Wait for a coherent pair of frames: depth and color
                    frames = self.pipeline.wait_for_frames()

                    # Create alignment primitive with color as its target stream:
                    align = rs.align(rs.stream.color)
                    frames = align.process(frames)

                    depth_frame = frames.get_depth_frame()
                    if not depth_frame:
                        raise Exception('Depth Frame requested but not available')

                    color_frame = frames.get_color_frame()
                    if not color_frame:
                        raise Exception('Color Frame requested but not available')

                    # Apply post-processing to depth-frame
                    filtered_frame = self.post_process_depth_frame(depth_frame)
                    # Calculate and log distance to procesed frame center
                    self.log_distance_to_image_center(filtered_frame)

                    # Convert frames to numpy arrays
                    depth_image = np.asanyarray(depth_frame.get_data())
                    filtered_depth_image = np.asanyarray(filtered_frame.get_data())
                    color_image = np.asanyarray(color_frame.get_data())

                    # Apply colormap on depth image
                    depth_colormap = np.asanyarray(rs.colorizer().colorize(depth_frame).get_data())
                    processed_depth_colormap = np.asanyarray(rs.colorizer().colorize(filtered_frame).get_data())

                    # ComputerVision models expect images to be of the same size as what was trained against.
                    # Below will resze the color, depth and color map images accordingly.
                    color_image = self.resize_image(color_image, resize_width, resize_height)
                    depth_colormap = self.resize_image(depth_colormap, resize_width, resize_height)
                    processed_depth_colormap = self.resize_image(processed_depth_colormap, resize_width, resize_height)

                    # Save depth and color image to local file as JPG
                    cv2.imwrite(DEPTH_IMAGE_PATH, depth_image)
                    cv2.imwrite(DEPTH_COLORMAP_PATH, depth_colormap)
                    cv2.imwrite(PROCESSED_DEPTH_COLORMAP_PATH, processed_depth_colormap)
                    cv2.imwrite(COLOR_IMAGE_PATH, color_image)

                    time.sleep(1.0)

                except KeyboardInterrupt:
                    log.info('Exiting.....')
                    sys.exit()

        except Exception as e:
            print(repr(e))

        finally:
            self.pipeline.stop()
            log.info('Pipeline successfully closed on {} - Serial {}'.format(self.rs_name, self.rs_serial))

    def resize_image(self, image, width, height):
        return cv2.resize(image, (width, height))

    def post_process_depth_frame(self, depth_frame, decimation_magnitude=2.0, spatial_magnitude=2.0, spatial_smooth_alpha=0.5,
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

    def log_distance_to_image_center(self, filtered_frame):

        center_width = int(filtered_frame.get_width() / 2)
        center_height = int(filtered_frame.get_height() / 2)

        zDepth = filtered_frame.get_distance(center_width, center_height)
        zDepth = '{:.3f}'.format(zDepth)
        log.info('Distance to image center at {} x {} is: {} meters'.format(center_width, center_height, zDepth))

if __name__ == "__main__":
    # Save the image to Pi Desktop to test
    rs_cam01 = RealsenseDevice()
    rs_cam01.capture_image(512, 512)