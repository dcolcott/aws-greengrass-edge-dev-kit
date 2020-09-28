#
# AWS IoT Greengrass Edge Devic Computer Vision Depth Perception
# Deployed to an AWS GreenGrass core with a Intel realSense 3D Depth Camera and Intel Neural COmpute Stick 2
#
# Performs hardware accellerated machine learning inference (using the Neural Compute Stick) on a RBG image 
# captured from the RealSense 3D depth camera. If a object is detected (as determned bt the ML model in use)
# then the distance to the object is calculated using the RealSense depth camera. The object tyope and distance is reported 
# to the AWS IoT Core using MQTT topic: edge-dev-kit/edge-cv/depth
#
# Workflow is as follows:
# 1) Take a color and depth frame from the RealSense Device,
# 2) Perform an inference against an Intel face-detect model (could be any model) loaded on the Intel Neural Compute Stick and
# 3) If an object is detected by the ML object-detection Model:
#   a) Performs post-processing on the depth frame and 
#   b) Takes a depth measurement to the center of the object bounding box on the processed frame using the RealSense Device depth functionality.
#   c) Reports the object type and distance to MQTT topic: edge-dev-kit/edge-cv/depth
# 4) Once every 30 seconds the average frame rate being processed by the AWS IoT Copre is posted to MQTT Topic: edge-dev-kit/edge-cv/depth/framerate
#
#  Note: Uses the RealSense Advanced class that applies one of a library of a pre-set configurations with various 
#  objectives to optimise density, accuracy, range and resolution and also offers post-processing of the depth frame before a depth calculation is made
#
#
# Author: Dean Colcott - https://www.linkedin.com/in/deancolcott/
#

import re
import subprocess

import sys
import cv2
import os
import logging
import traceback
import greengrasssdk
from threading import Timer
from neural_compute.intel_ncs import IntelNcs as Ncs
from realsense.realsense_advanced import RealsenseDevice as RealSenseAdvanced


# Config the logger.
log = logging.getLogger(__name__)
logging.basicConfig(format="%(name)s - [%(levelname)s] - %(message)s", stream=sys.stdout, level=logging.DEBUG)


# Inference Confidance threashold needed to register a detected object and post to MQTT
CONFIDENCE_THREASHOLD = 0.5

# name of model to use for object detection.
ML_MODEL_NAME = 'face-detection-adas-0001'

# If running lambda as non-containerised GreenGrass then prefix any resource paths with AWS_GG_RESOURCE_PREFIX
ML_MODEL_BASE_PATH = "{}{}".format(os.getenv("AWS_GG_RESOURCE_PREFIX"), "/ml/od/")

# Just for developmnet have manually added the modeks to Greengrass Core in /tmp
ML_MODEL_BASE_PATH = '/tmp'

# Interval (in seconds) to publish received framerate to MQTT
framerate_update_interval = 30

# Creating a greengrass core sdk client
client = greengrasssdk.client("iot-data")

# Number of saved frames in current framerate_update_interval.
frame_rate = 0

def post_log(message, mqtt_topic):
    """
    Simple helper to log and post a message to MQTT in same action. 
    """

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
        post_log(message, "edge-dev-kit/edge-cv/depth/framerate")

    except Exception as e:
        post_log(repr(e), "edge-dev-kit/edge-cv/depth/framerate/error")

    finally:
        # Reset frame_rate to 0 and re-run this Frame Rate notification function in framerate_update_interval seconds.
        frame_rate = 0
        Timer(framerate_update_interval, post_frame_rate).start()

def depth_measure_workflow():
    """
    Perform workflow to take an image from the RealSense device, peform an inference on the Compute Stick and 
    if an object detected, to log an dpost the depth to the first detected object. 
    """
    try:

        # Initilising Realsense camera.
        post_log('Initilising Realsense camera.', 'edge-dev-kit/edge-cv/depth/realsense')
        rs = RealSenseAdvanced()
        rs_name = rs.get_device_name()
        rs_serial = rs.get_device_serial()
        post_log('Successfully Initilised: {} - Serial no: {}'.format(rs_name, rs_serial), 'edge-dev-kit/edge-cv/depth/realsense/{}'.format(rs_serial))

        post_log('Initilising Intel Neural Compute Stick.', 'edge-dev-kit/edge-cv/depth/ncs')
        
        # get the model ( Neural Compute Stick .xml) expected path:
        model = os.path.join(ML_MODEL_BASE_PATH, ML_MODEL_NAME) +'.xml'
        # get the model weights ( Neural Compute Stick .bin) expected path:
        weights = os.path.join(ML_MODEL_BASE_PATH, ML_MODEL_NAME) +'.bin'
        # Initilise the Neural Compute Stick with the selected model.
        ncs = Ncs(model, weights)
        post_log('Successfully Initilised Neural Compute Stick', 'edge-dev-kit/edge-cv/depth/ncs')
        
        # Loop sleep delay (if used)
        sleep_iteration = 2
        
        confidence_threashold = CONFIDENCE_THREASHOLD

        while(True):

            log.debug('Getting color and depth frame from Realsense  as NP array')
            rs_frames = rs.get_rbg_depth_frames()

            # Convert to Np array and depth color map. 
            rs_frames_np = rs.get_frames_as_np_array(rs_frames)
            rbg = rs_frames_np['color_frame_np']
            depth_colormap = rs_frames_np['depth_frame_np']

            log.debug('Peforming Inference.........')
            boxes = ncs.peform_inference(rbg, confidence_threashold)

            if(len(boxes) <= 0):
                log.debug("No Objected Detected / Found")
            else:
                log.debug("Found / Detected: {} objects".format(len(boxes)))
                box = boxes[0][0]
                center_pt = get_box_center(box)
                log.debug('Calculating depth to first object at: {}'.format(center_pt))

                # Get Filtered / Post-Processed depth frame to improve quality / result
                log.debug('Applying filtering / post-processing to depth frame')
                filtered_frame = rs.get_post_process_depth_frame(rs_frames['depth_frame'])
                filtered_colormap = rs.get_frames_as_np_array({'filtered_frame' : filtered_frame})
                filtered_colormap = filtered_colormap['filtered_frame_np']

                # TODO: FIltered frame changes the image size, need to move above the inference 
                # or get the size difference to calculate the bounding box.
                # For now, just take depth from non-filtered depth frame.
                zDepth = rs.get_distance_to_frame_pixel(rs_frames['depth_frame'], center_pt['x'], center_pt['y'])
                post_log('Detected an object at: {} meters\n'.format(zDepth), 'edge-dev-kit/edge-cv/depth/realsense/{}'.format(rs_serial))

                # Uncomment below to save the latest processed (box-bound) image and depth color map locally if desired
                # Mote1: Images are saved on the AWS IoT Core device relative to the Greengrass Lambda which will need wrote permission for the location
                # Note2: Be careful if saving unique image names as will quickly fill up a AWS Iot Core device disk
                # Note3: Saving to file will impact the frame rate the AWS Iot Core device is capable of. 

                #save_box_bound_Image(rbg, "/tmp/image.bmp", boxes[0], "Person: {} meters".format(zDepth))
                #save_box_bound_Image(depth_colormap, "/tmp/colormap.bmp", boxes[0], "Person: {} meters".format(zDepth))
                #save_box_bound_Image(filtered_colormap, "/tmp/filtered_colormap.bmp", boxes[0], "Person: {} meters".format(zDepth))

            # Uncomment below to add a sleep dely between taking frames if desired
            #print('Sleeping for: {} seconds\n\n'.format(sleep_iteration))
            #time.sleep(sleep_iteration)

    except Exception as e:
        post_log(traceback.format_exc(), 'edge-dev-kit/edge-cv/depth/error')
    
    finally:
        # This function should run in an infiate loop unless an exceptuon is thrown.
        # In that case clear the connection to the RealSense camera, wait 30 seconds (10 secs for dev) then initilise and start again.
        rs.close_realsense_connection()
        Timer(10, depth_measure_workflow).start()
    
def save_box_bound_Image(image, saveas_path, boxes, annatation=None):

    for box in boxes:
        cv2.rectangle(image, (box[0], box[1]), (box[2], box[3]), (0, 0, 255), 2)

    if annatation:
        font = cv2.FONT_HERSHEY_SIMPLEX
        org = (box[0], box[1] -5)
        fontScale = 0.75
        color = (0, 0, 255)
        thickness = 1
        image = cv2.putText(image, annatation, org, font, fontScale, color, thickness, cv2.LINE_AA) 
        
    cv2.imwrite(saveas_path, image)

def get_box_center(box):
    xmin, ymin, xmax, ymax = box
    x_center = int(xmin + ((xmax - xmin) / 2))
    y_center = int(ymin + ((ymax - ymin) / 2))
    return {'x': x_center, 'y': y_center}

#######################################################
# Start the greengrass_realsense_depth() and framerate_update_interval as threads. 
Timer(0, depth_measure_workflow()).start()
Timer(framerate_update_interval, post_frame_rate).start()

# Just a dummy handler for AWS lambda, it will not be invoked
def lambda_handler(event, context):
    return
