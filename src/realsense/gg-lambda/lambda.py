#
# Copyright 2010-2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#

# gg_realsense_lambbda.py
# Runs in AWS GreenGrass core RAsPi4 with RealSesse, OPenCV and NumPy installed.
# Takes color and depth image from RealSense d345 (USB Cam) and saves
# To device locally.
#
import os
import logging
import sys
import pyrealsense2 as rs
import numpy as np
import cv2
from threading import Timer
import greengrasssdk

resourcePath = "{}{}".format(os.getenv("AWS_GG_RESOURCE_PREFIX"), "/trained_models")

# Local vars for update and image save path.
framerate_update_interval = 10  # Interval (in seconds) to publish received framerate to MQTT
depth_image_path = '/home/pi/depth_image.jpg'
color_image_path = '/home/pi/color_image.jpg'

# Setup logging to stdout
logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

# Creating a greengrass core sdk client
client = greengrasssdk.client("iot-data")

# Configure realsense depth and color streams
pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.depth, 848, 480, rs.format.z16, 30)
config.enable_stream(rs.stream.color, 848, 480, rs.format.bgr8, 30)

# Start real sense camera streaming
pipeline.start(config)

# Rate of saved frames.
frame_rate = 0

def post_frame_rate():
  global frame_rate
  try:
    avged_frame_rate = round((frame_rate / framerate_update_interval), 2)
    client.publish(
      topic="dcolcott/raspi4/realsense/framerate",
      queueFullPolicy="AllOrException",
      payload="RealSense RasPi4 capturing {} fps".format(avged_frame_rate)
    )
    
    # For debug only:
    print("resourcePath: {} ".format(resourcePath))

  except Exception as e:
    client.publish(
      topic="dcolcott/raspi4/realsense/error",
      queueFullPolicy="AllOrException",
      payload="ERROR: {}".format(repr(e))
    )

  finally:
    # Reset frame_rate to 0 and re-run this Frame Rate notification function in 1Sec
    frame_rate = 0
    Timer(framerate_update_interval, post_frame_rate).start()


def greengrass_realsense_save_images():
  global frame_rate
  try:
    # Wait for a coherent pair of frames: depth and color
    frames = pipeline.wait_for_frames()

    #depth_frame = frames.get_depth_frame()
    #if not depth_frame:
    #    raise Exception('Depth Frame requested but not available')

    color_frame = frames.get_color_frame()
    if not color_frame:
        raise Exception('Color Frame requested but not available')

    # Convert images to numpy arrays
    #depth_image = np.asanyarray(depth_frame.get_data())
    color_image = np.asanyarray(color_frame.get_data())

    # Apply colormap on depth image (image must be converted to 8-bit per pixel first)
    #depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET)

    # Save depth and color image to local file as JPG
    #cv2.imwrite(depth_image_path, depth_colormap)
    cv2.imwrite(color_image_path, color_image)
    
    # Increment frame rate for this time interval
    frame_rate += 1

  except Exception as e:
    logger.error("ERROR greengrass_realsense_save_images():" + repr(e))
    client.publish(
        topic="dcolcott/raspi4/realsense/error",
        queueFullPolicy="AllOrException",
        payload="ERROR: {}".format(repr(e))
    )

  finally:
    # Re-run this image capture function in 50ms.
    Timer(0.05, greengrass_realsense_save_images).start()

# Start the image capture and 'framerate_update_interval' seconds later start post_frame_rate()
Timer(0, greengrass_realsense_save_images).start()
Timer(framerate_update_interval, post_frame_rate).start()

# This is a dummy handler for AWS lambda and will not be invoked
# Instead the code above will be executed in an infinite loop for our example
def function_handler(event, context):
    return
