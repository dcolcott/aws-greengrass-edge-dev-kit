# realsense-simple.py
#
# Takes colour and depth image from the Intel RelSense 3D camera using mostly simple 
# defaults and no image post processing
# Calculates and logs the distance to the center of the image frame. 
# 
# Author: Dean Colcott - https://www.linkedin.com/in/deancolcott/
#
#
import pyrealsense2 as rs
import numpy as np
import logging as log
import time
import sys
import cv2

# Config the  logger.
log.basicConfig(format="[ %(levelname)s ] %(message)s", level=log.INFO, stream=sys.stdout)

# Image file save location.
DEPTH_IMAGE_PATH = '/home/pi/Desktop/depth_image.jpg'
DEPTH_COLORMAP_PATH= '/home/pi/Desktop/depth_colormap.jpg'
COLOR_IMAGE_PATH = '/home/pi/Desktop/color_image.jpg'

class RealsenseDevice():
    """
    Captured a RGB and Depth image from the first discovered Realsense camera and save to a local file.
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

    def capture_image(self):

        try:
            # Skip 5 first frames to give the Auto-Exposure time to adjust
            log.info('Captured realsense image - waiting for auto-exposure to adjust')
            for x in range(5):
               self.pipeline.wait_for_frames()
               log.info('Captured wait frame: {}'.format(x))

            log.info('Starting depth image processing, press Ctl-C to exit.')

            while(True):

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

                # Convert images to numpy arrays
                depth_image = np.asanyarray(depth_frame.get_data())
                color_image = np.asanyarray(color_frame.get_data())
                # Apply colormap on depth image
                depth_colormap = np.asanyarray(rs.colorizer().colorize(depth_frame).get_data())

                # Save depth and color image to local file as JPG
                cv2.imwrite(DEPTH_IMAGE_PATH, depth_image)
                cv2.imwrite(DEPTH_COLORMAP_PATH, depth_colormap)
                cv2.imwrite(COLOR_IMAGE_PATH, color_image)

                self.get_distance_to_image_center(depth_frame)
                time.sleep(1.0)

        except KeyboardInterrupt:
            log.info('Exiting.....')
            sys.exit()
 
        except Exception as e:
            print(repr(e))

        finally:
            self.pipeline.stop()
            log.info('Pipeline successfully closed on {} - Serial {}'.format(self.rs_name, self.rs_serial))

    def get_distance_to_image_center(self, depth_frame):

        center_width = int(depth_frame.get_width() / 2)
        center_height = int(depth_frame.get_height() / 2)

        zDepth = depth_frame.get_distance(center_width, center_height)
        zDepth = '{:.3f}'.format(zDepth)
        log.info('Distance to image center at {} x {} is: {} meters'.format(center_width, center_height, zDepth))

if __name__ == "__main__":
    # Save the image to Pi Desktop to test
    rs_cam01 = RealsenseDevice()
    rs_cam01.capture_image()