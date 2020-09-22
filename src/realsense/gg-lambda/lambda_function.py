#
# Copyright 2010-2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#

# gg_realsense_simple_depth
# Runs in AWS GreenGrass core RAsPi4 with RealSesse, OPenCV and NumPy installed.
# Takes a depth and color image frame, logs to SystOut and MQTT the depth measured tp
# the center of the current realsense frame. 
#
import os
import logging
import sys
import greengrasssdk
from threading import Timer
from realsense.realsense_simple import RealsenseDevice as RealsenseSimple
from realsense.realsense_advanced import RealsenseDevice as RealsenseAdvanced

# Config the logger.
log = logging.getLogger(__name__)
logging.basicConfig(
    format="%(asctime)s - %(name)s - [%(levelname)s] - %(message)s", stream=sys.stdout, level=logging.INFO)

# Local vars for update and image save path.
# Interval (in seconds) to publish received framerate to MQTT
framerate_update_interval = 10

# Creating a greengrass core sdk client
client = greengrasssdk.client("iot-data")

# Rate of saved frames.
frame_rate = 0

def post_log(message, mqtt_topic):

    log.info(message)
    
    client.publish(
        topic=mqtt_topic,
        queueFullPolicy="AllOrException",
        payload=message
    )

def post_frame_rate():
    global frame_rate
    try:
        avged_frame_rate = round((frame_rate / framerate_update_interval), 2)
        message = "RealSense RasPi4 capturing {} fps".format(avged_frame_rate)
        post_log(message, "gg-edge-kit/realsense/framerate")

    except Exception as e:
        post_log(repr(e), "gg-edge-kit/realsense/framerate/error")

    finally:
        # Reset frame_rate to 0 and re-run this Frame Rate notification function in 1Sec
        frame_rate = 0
        Timer(framerate_update_interval, post_frame_rate).start()

def greengrass_realsense_depth():

    try:
        global frame_rate
        zDepth = rs_device.get_distance_to_frame_pixel()
        message = 'Distance to image center is: {} meters'.format(zDepth)
        post_log(message, "gg-edge-kit/realsense/depth")

        # Increment frame rate for this time interval
        frame_rate += 1

    except Exception as e:
        post_log(repr(e), "gg-edge-kit/realsense/depth/error")

    finally:
        # Re-run this image capture function in 500ms.
        Timer(0.50, greengrass_realsense_depth).start()


# Start the image capture and 'framerate_update_interval' seconds later start post_frame_rate()
post_log('Initialising Real Sense Device', 'gg-edge-kit/realsense')

# Select the simple or advance config and feature set by swapping the rs_device comment below:
rs_device = RealsenseSimple()
# rs_device = RealsenseAdvanced()

# Start the greengrass_realsense_depth() and framerate_update_interval as threads. 
Timer(0, greengrass_realsense_depth()).start()
Timer(framerate_update_interval, post_frame_rate).start()

# This is a dummy handler for AWS lambda and will not be invoked
# Instead the code above will be executed in an infinite loop for our example
def lambda_handler(event, context):
    return
