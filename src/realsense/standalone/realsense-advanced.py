#
# Copyright 2010-2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Takes and if needed resizes a colour or depth image from the Intel RelSense 3d camera
# 
# Visual presets from: https://github.com/IntelRealSense/librealsense/wiki/D400-Series-Visual-Presets
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

# Image file save location.
depth_image_path = '/home/pi/Desktop/depth_image.jpg'
pointcloud_path = '/home/pi/Desktop/pointcloud.ply'
depth_colourmap_path = '/home/pi/Desktop/depth_colormap.jpg'
processed_depth_colourmap_path = '/home/pi/Desktop/processed_depth_colormap.jpg'
color_image_path = '/home/pi/Desktop/color_image.jpg'

class RealsenseDevice():
    """
    Captured a RGB and Depth image from the Realsense D453i camera and saves to a local file.
    """
    def __init__(self):

        log.info('Initilising Realsense Camera')
        # Configure realsense device, 
        self.pipeline = rs.pipeline()
        self.config = rs.config()
        self.profile = self.config.resolve(self.pipeline)

        # Load stream values from predefined config file. 
        self.set_stream_config("preset-configs/DefaultPreset_D435.json")

        # Configure depth and color streams (could also add IR stream if desired)
        self.config.enable_stream(rs.stream.depth, self.stream_width, self.stream_height, rs.format.z16, self.stream_fps)
        self.config.enable_stream(rs.stream.color, self.stream_width, self.stream_height, rs.format.bgr8, self.stream_fps)

        # Start real sense camera streaming
        self.cfg = self.pipeline.start(self.config)

        # (optional) Set advanced settings on Realsense Camera
        self.set_advanced_settings(self.cfg)

        self.rs_name = self.profile.get_device().get_info(rs.camera_info.name)
        self.rs_serial = self.profile.get_device().get_info(rs.camera_info.serial_number)
        log.info('{} - Serial:{} Successfully Initilised'.format(self.rs_name, self.rs_serial))

    def set_stream_config(self, config_file):
        # Configure advanced mode settings taken from realsense-viewer
        self.json_config = json.load(open(config_file))
        self.json_string_config = str(self.json_config).replace("'", '\"')

        self.stream_width = int(self.json_config['stream-width'])
        self.stream_height = int(self.json_config['stream-height'])
        self.stream_fps = int(self.json_config['stream-fps'])

    def set_advanced_settings(self, cfg):
        # Apply advanced mode configs from config file. 
        self.dev = cfg.get_device()
        self.advnc_mode = rs.rs400_advanced_mode(self.dev)
        self.advnc_mode.load_json(self.json_string_config)

        # Sensor [0] is the depth sensor.
        depth_sensor = self.dev.query_sensors()[0]
        depth_sensor.set_option(rs.option.enable_auto_exposure, True)

    def capture_image(self, resize_width, resize_height):

        try:
            # Skip 5 first frames to give the Auto-Exposure time to adjust
            log.info('Caputure realsense image - waiting for auto-exposure to adjust')
            for x in range(5):
               self.pipeline.wait_for_frames()
               log.info('Captured wait frame: {}'.format(x))

            while(True):
                # Wait for a coherent pair of frames: depth and color
                self.frames = self.pipeline.wait_for_frames()

                # Create alignment primitive with color as its target stream:
                self.align = rs.align(rs.stream.color)
                self.frames = self.align.process(self.frames)

                self.depth_frame = self.frames.get_depth_frame()
                if not self.depth_frame:
                    raise Exception('Depth Frame requested but not available')

                self.color_frame = self.frames.get_color_frame()
                if not self.color_frame:
                    raise Exception('Color Frame requested but not available')

                # Convert images to numpy arrays
                self.filtered_depth_frame = self.post_process_depth_frame(self.depth_frame)

                self.depth_image = np.asanyarray(self.depth_frame.get_data())
                self.filtered_depth_image = np.asanyarray(self.filtered_depth_frame.get_data())
                self.color_image = np.asanyarray(self.color_frame.get_data())

                # Apply colormap on depth image (image must be converted to 8-bit per pixel first)
                self.depth_colormap = np.asanyarray(rs.colorizer().colorize(self.depth_frame).get_data())
                self.processed_depth_colormap = np.asanyarray(rs.colorizer().colorize(self.filtered_depth_frame).get_data())

                # ComputerVision models expect images to be of the same size as what was trained against.
                # Below will resze the color, depth and color map images accordingly.
                self.resize_images(resize_width, resize_height)

                # Save depth and color image to local file as JPG
                cv2.imwrite(depth_image_path, self.depth_image)
                cv2.imwrite(depth_colourmap_path, self.depth_colormap)
                cv2.imwrite(processed_depth_colourmap_path, self.processed_depth_colormap)
                cv2.imwrite(color_image_path, self.color_image)

                self.get_distance_to_image_center()

                time.sleep(1.0)

        except Exception as e:
            print(repr(e))

        finally:
            log.info('Capture frames on {} - Serial {} complete'.format(self.rs_name, self.rs_serial))
            self.pipeline.stop()
            log.info('Realsense pipeline successfully closed')

    def resize_images(self, width, height):
        self.color_image = cv2.resize(self.color_image, (width, height))
        self.depth_image = cv2.resize(self.depth_image, (width, height))
        self.depth_colormap = cv2.resize(self.depth_colormap, (width, height))
        self.processed_depth_colormap = cv2.resize(self.processed_depth_colormap, (width, height))

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

        return filtered_frame

    def get_distance_to_image_center(self):

        center_width = int(self.depth_frame.get_width() / 2)
        center_height = int(self.depth_frame.get_height() / 2)

        zDepth = self.depth_frame.get_distance(center_width, center_height)
        print('Distance to image center at {} x {} is: {}'.format(center_width, center_height, zDepth))

if __name__ == "__main__":
    # Save the image to Pi Desktop to test
    rs_cam01 = RealsenseDevice()
    rs_cam01.capture_image(512, 512)