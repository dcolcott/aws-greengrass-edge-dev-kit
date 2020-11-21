#
# AWS IoT Greengrass Edge Device Computer Vision Depth Perception
# Deployed to an AWS GreenGrass core with an Intel RealSense 3D Depth Camera and Intel Neural Compute Stick 2
#
# Performs hardware accelerated machine learning inference (using the Neural Compute Stick) on a RBG image 
# captured from the RealSense 3D depth camera. If an object is detected (as determined by the ML model in use)
# then the distance to the object is calculated using the RealSense depth camera. The object type and distance is reported 
# to the AWS IoT Core using MQTT topic: edge-dev-kit/edge-cv/depth
#
# Workflow is as follows:
# 1) Take a colour and depth frame from the RealSense Device,
# 2) Perform an inference against an Intel face-detect model (could be any model) loaded on the Intel Neural Compute Stick and
# 3) If an object is detected by the ML object-detection Model:
#   a) Performs post-processing on the depth frame and 
#   b) Takes a depth measurement to the center of the object bounding box on the processed frame using the RealSense Device depth functionality.
#   c) Reports the object type and distance to MQTT topic: edge-dev-kit/edge-cv/depth
# 4) Once every 30 seconds the average frame rate being processed by the AWS IoT Core is posted to MQTT Topic: edge-dev-kit/edge-cv/depth/framerate
#
#  Note: Uses the RealSense Advanced class that applies one of a library of a pre-set configurations with various 
#  objectives to optimise density, accuracy, range and resolution and also offers post-processing of the depth frame before a depth calculation is made
#
# Greengrass Container Parameters:
# Another user ID/group ID: 0
# Containerization: No Container (Always) / Timeout: 30
# Lambda lifecycle: Make this function long-lived and keep it running indefinitely
# All else to default
#
# The below env vars must be set in AWS Iot Greengrass as need to be avliable before the python VM is initilised
# so can't be added in py code as others provoded.
# Note: May need to change some values according to the platform, OS and realsense install. 
#
# PYTHONPATH = /usr/lib/python3/dist-packages/pyrealsense2:/opt/intel/openvino/python/python3.7:/opt/intel/openvino/python/python3:/opt/intel/openvino/deployment_tools/model_optimizer:
# LD_LIBRARY_PATH = /opt/intel/openvino/opencv/lib:/opt/intel/openvino/deployment_tools/ngraph/lib:/opt/intel/openvino/deployment_tools/inference_engine/external/hddl_unite/lib:/opt/intel/openvino/deployment_tools/inference_engine/external/hddl/lib:/opt/intel/openvino/deployment_tools/inference_engine/external/gna/lib:/opt/intel/openvino/deployment_tools/inference_engine/external/mkltiny_lnx/lib:/opt/intel/openvino/deployment_tools/inference_engine/external/tbb/lib:/opt/intel/openvino/deployment_tools/inference_engine/lib/armv7l:
#
# Author: Dean Colcott - https://www.linkedin.com/in/deancolcott/
#
import os
import re
import sys
import cv2
import json
import time
import logging
import traceback
import subprocess
import greengrasssdk
from threading import Timer

# Env vars that need to be set before initilising the Realsense or Intel Neural Compute stick
# These may need to be changed depenbding on the platform and openvino install.
# TODO: Move these to an external config file and read in.
os.environ["InferenceEngine_DIR"] = "/opt/intel/openvino/deployment_tools/inference_engine/share"
os.environ["INTEL_OPENVINO_DIR "] = "/opt/intel/openvino"
os.environ["KMB_INSTALL_DIR "] = "/opt/intel/openvino/deployment_tools/inference_engine/external/hddl_unite"
os.environ["OpenCV_DIR"] = "/opt/intel/openvino/opencv/cmake"
os.environ["ngraph_DIR"] = "/opt/intel/openvino/deployment_tools/ngraph/cmake"
os.environ["HDDL_INSTALL_DIR"] = "/opt/intel/openvino/deployment_tools/inference_engine/external/hddl"
os.environ["INTEL_CVSDK_DIR"] = "/opt/intel/openvino"

from neural_compute.intel_ncs import IntelNcs as Ncs
from realsense.realsense_advanced import RealsenseDevice as RealSenseAdvanced

# Config the logger.
log = logging.getLogger(__name__)
logging.basicConfig(format="%(name)s - [%(levelname)s] - %(message)s", stream=sys.stdout, level=logging.INFO)

# Inference Confidence threshold needed to register a detected object and post to MQTT
CONFIDENCE_THRESHOLD = 0.5

# Parent directory to save processed image and depth colour map (for dev on Rasp Pi)
IMAGE_SAVE_DIR = '/home/pi/Desktop'

# Just for development, manually add the Intel model files (.bin and .xml) to Greengrass Core in /home/pi/compute-stick-build/
ML_MODEL_BASE_PATH = '/home/pi/Documents/compute-stick-build/'

# name of model to use for object detection.
ML_MODEL_NAME = 'face-detection-adas-0001'

# If running lambda as non-containerised GreenGrass then prefix any resource paths with AWS_GG_RESOURCE_PREFIX
# ML_MODEL_BASE_PATH = "{}{}".format(os.getenv("AWS_GG_RESOURCE_PREFIX"), "/ml/od/")

# Just for development, manually add the Intel model files (.bin and .xml) to Greengrass Core (RasPi in this case) to /home/pi/compute-stick-build/
ML_MODEL_BASE_PATH = '/home/pi/Documents/compute-stick-build/'

# Interval (in seconds) to publish received framerate to MQTT
framerate_update_interval = 30

# Creating a GreenGrass core sdk client
client = greengrasssdk.client("iot-data")

# Number of saved frames in current framerate_update_interval.
frame_rate = 0

def post_log(message, mqtt_topic):
    """
    Simple helper to log and post a message to MQTT in same action. 
    """

    log.info('{} - {}'.format(mqtt_topic, message))
    
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
    Perform workflow to take an image from the RealSense device, perform an inference on the Neural Compute Stick and 
    if an object detected, to log and post the depth to the first detected object. 
    """
    
    try:
        
        global frame_rate

        # Initializing RealSense camera.
        post_log('Initilising Realsense camera.', 'edge-dev-kit/edge-cv/depth/realsense')
        rs = RealSenseAdvanced()
        rs_name = rs.get_device_name()
        rs_serial = rs.get_device_serial()
        post_log('Successfully Initilised: {} - Serial no: {}'.format(rs_name, rs_serial), 'edge-dev-kit/edge-cv/depth/{}'.format(rs_serial))

        post_log('Initializing Intel Neural Compute Stick.', 'edge-dev-kit/edge-cv/depth/ncs')
        
        # get the model ( Neural Compute Stick .xml) expected path:
        model = os.path.join(ML_MODEL_BASE_PATH, ML_MODEL_NAME) +'.xml'
        # get the model weights ( Neural Compute Stick .bin) expected path:
        weights = os.path.join(ML_MODEL_BASE_PATH, ML_MODEL_NAME) +'.bin'
        # Initialize the Neural Compute Stick with the selected model.
        ncs = Ncs(model, weights)
        post_log('Successfully Initialized Neural Compute Stick', 'edge-dev-kit/edge-cv/depth/ncs')
        
        # Image procesisng sleep delay (Secs). Make sure is at least 0.05
        sleep_iteration = 2
        
        confidence_threshold = CONFIDENCE_THRESHOLD

        while(True):

            log.debug('Getting color and depth frame from Realsense  as NP array')
            rs_frames = rs.get_rbg_depth_frames()

            # Convert to Np array and depth colour map. 
            rs_frames_np = rs.get_frames_as_np_array(rs_frames)
            rbg = rs_frames_np['color_frame_np']
            depth_colormap = rs_frames_np['depth_frame_np']
            
            # Get Filtered / Post-Processed depth frame to improve quality / result
            log.info('Applying filtering / post-processing to depth frame')
            filtered_frame = rs.get_post_process_depth_frame(rs_frames['depth_frame'])
            filtered_colormap = rs.get_frames_as_np_array({'filtered_frame': filtered_frame})
            filtered_colormap = filtered_colormap['filtered_frame_np']

            # Peform object detect inference which is returned as dict of detected classes
            # holdng an array of detected object box coordinates such as:
            # {"0": [[446, 290, 515, 380], [602, 96, 625, 121]]}
            log.debug('Performing Inference.........')
            inf_result = ncs.perform_inference(rbg, confidence_threshold)

            # For each class identified by the object detection model, get the distance to each
            # identified object and annotate the image with boxes and class / distance labels
            for obj_class in inf_result:

                for box in inf_result[obj_class]:

                    # Get center of detected object box bounding
                    x1, y1, x2, y2 = box
                    x_center = int(x1 + ((x2 - x1) / 2))
                    y_center = int(y1 + ((y2 - y1) / 2))

                    # Get distance to center of detected object box bounding
                    zDepth = rs.get_distance_to_frame_pixel(rs_frames['depth_frame'], x_center, y_center)
                    log.debug('Identified Object Class: {} Distance: {} Object Co-ordinates: {}'.format(obj_class, zDepth, box))

                    # append box coordinates with depth to object and object class
                    box.append(obj_class)
                    box.append(zDepth)

                    # Annotate the box and distance label to the respective frames
                    annotate_image_frames(rs_frames_np, box)

            # Log the image inference results
            post_log( json.dumps({ 'inference_result' : inf_result }), 'edge-dev-kit/edge-cv/depth/'.format(rs_serial))
 
            # Uncomment below to save the latest processed (box-bound) image and depth colour map locally if desired
            # Note: Be careful if saving unique image names with a high loop count as will quickly fill up the local disk
            save_box_bound_Image(rbg, "image.bmp")
            save_box_bound_Image(depth_colormap, "colormap.bmp")
            save_box_bound_Image(filtered_colormap, "filtered_colormap.bmp")

            # Inc image processed count
            frame_rate += 1

            # Add a sleep dely between taking frames, can make the device unreachable if no delay at all. 
            time.sleep(sleep_iteration)

    except Exception as e:
        post_log(traceback.format_exc(), 'edge-dev-kit/edge-cv/depth/error')
    
    finally:
        # This function should run in an infinite loop unless an exception is thrown.
        # In that case clear the connection to the RealSense camera, wait 30 seconds (10 secs for dev) then initialize and start again.
        rs.close_realsense_connection()
        Timer(30, depth_measure_workflow).start()

def annotate_image_frames(np_frames, box):

    x1, y1, x2, y2, obj_class, distance = box

    for key in np_frames:
        
        # Annotate the image label with object class and distance
        label = '{} : {} meters'.format(obj_class, distance)
        font = cv2.FONT_HERSHEY_SIMPLEX
        org = (x1, y1 - 5)
        fontScale = 0.5
        color = (0, 0, 255)
        weight = 1
        cv2.putText(np_frames[key], label, org, font, fontScale, color, weight, cv2.LINE_AA) 

        # Annotate the object bounding box
        thickness = 2
        cv2.rectangle(np_frames[key], (x1, y1), (x2, y2), color, thickness)

def save_box_bound_Image(image, saveas):
    saveas_path = os.path.join(IMAGE_SAVE_DIR, saveas)   
    cv2.imwrite(saveas_path, image)

#######################################################
# Start the greengrass_realsense_depth() and framerate_update_interval as threads. 
Timer(0, depth_measure_workflow()).start()
Timer(framerate_update_interval, post_frame_rate).start()

# Just a dummy handler for AWS lambda, it will not be invoked
def lambda_handler(event, context):
    return


