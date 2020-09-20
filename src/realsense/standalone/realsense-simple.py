#
#
# Takes colour and depth image from the Intel RelSense 3d camera
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
depth_image_path = '/home/pi/Desktop/depth_image.jpg'
depth_colourmap_path = '/home/pi/Desktop/depth_colormap.jpg'
color_image_path = '/home/pi/Desktop/color_image.jpg'

class RealsenseDevice():
    """
    Captured a RGB and Depth image from the first discovered Realsense camera and save to a local file.
    """

    def __init__(self):

        log.info('Initilising Realsense Camera')
        # Configure realsense device, 
        self.pipeline = rs.pipeline()
        self.config = rs.config()
        self.profile = self.config.resolve(self.pipeline)

        # Configure depth and color streams (can also add IR stream if desired)
        self.config.enable_stream(rs.stream.depth, 848, 480, rs.format.z16, 15)
        self.config.enable_stream(rs.stream.color, 848, 480, rs.format.bgr8, 15)

        # Start real sense camera streaming
        self.pipeline.start(self.config)

        self.rs_name = self.profile.get_device().get_info(rs.camera_info.name)
        self.rs_serial = self.profile.get_device().get_info(rs.camera_info.serial_number)
        log.info('{} - Serial:{} Successfully Initilised'.format(self.rs_name, self.rs_serial))

    def capture_image(self):

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
                self.depth_image = np.asanyarray(self.depth_frame.get_data())
                self.color_image = np.asanyarray(self.color_frame.get_data())

                # Apply colormap on depth image
                self.depth_colormap = np.asanyarray(rs.colorizer().colorize(self.depth_frame).get_data())

                # Save depth and color image to local file as JPG
                cv2.imwrite(depth_image_path, self.depth_image)
                cv2.imwrite(depth_colourmap_path, self.depth_colormap)
                cv2.imwrite(color_image_path, self.color_image)

                self.get_distance_to_image_center()
                time.sleep(1.0)
 
        except Exception as e:
            print(repr(e))

        finally:
            log.info('Capture frames on {} - Serial {} complete'.format(self.rs_name, self.rs_serial))
            self.pipeline.stop()
            log.info('Realsense pipeline successfully closed')

    def get_distance_to_image_center(self):

        center_width = int(self.depth_frame.get_width() / 2)
        center_height = int(self.depth_frame.get_height() / 2)

        zDepth = self.depth_frame.get_distance(center_width, center_height)
        print('Distance to image center at {} x {} is: {}'.format(center_width, center_height, zDepth))


if __name__ == "__main__":
    # Save the image to Pi Desktop to test
    rs_cam01 = RealsenseDevice()
    rs_cam01.capture_image()