#
# A test method to run a workflow on the Raspberry Pi that will:
# 1) Take a colour and depth frame from the RealSense Device,
# 2) Performs an inference against an Intel face-detect model (could be any model) on the Intel Neural Compute Stick and
# 3) If an object is detected:
#   a) Performs post-processing on the depth frame and
#   b) Takes a depth measurement to the center of the object bounding box on the processed frame using the RealSense Device depth functionality.
# 4) Saves the processed / box bound RBG and Depth Frame to the Pi user Desktop (update location for other users)
# 5) Repeats the process after a defined wait period.
#
#  Note: Uses the RealSense Advanced class that applies one of a library of a pre-set configurations with various
#  objectives to optimise density, accuracy, range and resolution and also offers post-processing of the depth frame before a depth calculation is made
#
# Calls the same classes and functions as the AWS Greengrass Lambda to interact with the
# RealSense Device and the Intel Neural Compute stick so is a convenient way to develop and try out new functions locally.
#
# Author: Dean Colcott - https://www.linkedin.com/in/deancolcott/
#
# Example use:
# 1) Connect the RealSense camera and Neural Compute Stick to the USB3 ports,
# 2) Load the desired Intel model into a directory:/home/pi/Documents/compute-stick-build/ (or update ML_MODEL_BASE_PATH below),
# 3) Update the ML_MODEL_NAME
# 3) CD into the src directory: cd src/
# 4) Execute the workflow: python3 workflow-tests/workflow-cv-depth-simple.py
#

import os
import sys
import time
import cv2
import logging
import traceback
from neural_compute.intel_ncs import IntelNcs as Ncs
from realsense.realsense_advanced import RealsenseDevice as RealSenseAdvanced

# Config the logger.
log = logging.getLogger(__name__)
logging.basicConfig(
    format="%(asctime)s - %(name)s - [%(levelname)s] - %(message)s", stream=sys.stdout, level=logging.INFO)

# Inference Confidence threshold needed to register a detected object in RealSense image
CONFIDENCE_THRESHOLD = 0.5

# Parent directory to save processed image and depth colour map (for dev on Rasp Pi)
IMAGE_SAVE_DIR = '/home/pi/Desktop'

# Just for development, manually add the Intel model files (.bin and .xml) to Greengrass Core in /home/pi/compute-stick-build/
ML_MODEL_BASE_PATH = '/home/pi/Documents/compute-stick-build/'

# name of model to use for object detection.
ML_MODEL_NAME = 'face-detection-adas-0001'

# Just for development, manually added the Intel model files (.bin and .xml) to Greengrass Core (RasPi in this case) to /home/pi/compute-stick-build/
ML_MODEL_BASE_PATH = '/home/pi/Documents/compute-stick-build/'


def workflow_realsense_advanced():
    """
    Perform workflow to take an image for the RealSense device, perform an inference on the Neural Compute Stick and 
    if an object detected, to log the depth to the first detected object. 
    """
    try:

        # Initializing RealSense camera.
        log.info('\n##############################')
        log.info('Initializing RealSense camera.')
        rs = RealSenseAdvanced()
        rs_name = rs.get_device_name()
        rs_serial = rs.get_device_serial()
        log.info(
            'Successfully Initialized: {} - Serial no: {}'.format(rs_name, rs_serial))

        log.info('\n##############################')
        log.info('Initializing Intel Neural Compute Stick.')
        # get the model ( Neural Compute Stick .xml) expected path:
        model = os.path.join(ML_MODEL_BASE_PATH, ML_MODEL_NAME) + '.xml'
        # get the model weights ( Neural Compute Stick .bin) expected path:
        weights = os.path.join(ML_MODEL_BASE_PATH, ML_MODEL_NAME) + '.bin'
        # Initialize the Neural Compute Stick with the selected model.
        ncs = Ncs(model, weights)
        log.info('Successfully Initialized Neural Compute Stick')

        # Set the sleep time and loop iteration variables and start timer.
        sleep_iteration = 2
        image_cnt = 0
        start = time.time()

        confidence_threshold = CONFIDENCE_THRESHOLD

        log.info('Starting image inference loop.')

        while True:

            try:
                log.info(
                    'Getting colour and depth frame from RealSense as NP array')
                rs_frames = rs.get_rbg_depth_frames()

                # Convert to Np array and depth color map.
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
                log.info('Performing Inference against rbg frame.........')
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
                log.info('Image Infrence result: {}'.format(inf_result))

                # Uncomment below to save the latest processed (box-bound) image and depth colour map locally if desired
                # Note: Be careful if saving unique image names with a high loop count as will quickly fill up the local disk
                save_box_bound_Image(rbg, "image.bmp")
                save_box_bound_Image(depth_colormap, "colormap.bmp")
                save_box_bound_Image(filtered_colormap, "filtered_colormap.bmp")

                # Inc image processed count
                image_cnt += 1

                # Add a sleep delay between taking next frames.
                time.sleep(sleep_iteration)

            except KeyboardInterrupt:
                total_time = time.time() - start
                log.info("Completed {} image inference in {} seconds at {} Inference FPS".format(
                    image_cnt, total_time, image_cnt / total_time))
                sys.exit()

    except Exception as e:
        log.info(e)
        log.info(traceback.format_exc())

    finally:
        print('Closing RealSense Connection......')
        rs.close_realsense_connection()


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


if __name__ == "__main__":

    workflow_realsense_advanced()
