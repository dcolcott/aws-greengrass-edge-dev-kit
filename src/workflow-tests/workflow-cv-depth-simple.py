#
# A test method to run a workflow on the Raspberry Pi that will:
# 1) Take a colour and depth frame from the RealSense Device,
# 2) Performs an inference against an Intel face-detect model (could be any model) on the Intel Neural Compute Stick and
# 3) If an object is detected, takes a depth measurement to the center of the object bounding box on the processed frame using the RealSense Device depth functionality.
# 4) Saves the processed / box bound RBG and Depth Frame to the Pi user Desktop (update IMAGE_SAVE_DIR for another path)
# 5) Repeats the process after a defined wait period. 
#
#  Note: Uses the RealSense Simple class that loads a simple default configuration into the RealSense device and doesn't provide 
# any post-processing of the depth frame.
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
# 4) Execute the workflow: python3 workflow-tests/workflow-cv-depth-advanced.py
#


import os
import sys
import time
import cv2
import logging
import traceback
from neural_compute.intel_ncs import IntelNcs as Ncs
from realsense.realsense_simple import RealsenseDevice as RealSenseSimple

# Config the logger.
log = logging.getLogger(__name__)
logging.basicConfig(format="%(asctime)s - %(name)s - [%(levelname)s] - %(message)s", stream=sys.stdout, level=logging.INFO)

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

# Parent directory to save processed image and depth colour map
IMAGE_SAVE_DIR = '/home/pi/Desktop'

def workflow_realsense_simple():
    """
    Perform workflow to take an image for the RealSense device, perform an inference on the Neural Compute Stick and 
    if an object detected, to log the depth to the first detected object. 
    """
    try:

        # Initializing RealSense camera.
        log.info('\n##############################')
        log.info('Initializing RealSense camera.')
        rs = RealSenseSimple()
        rs_name = rs.get_device_name()
        rs_serial = rs.get_device_serial()
        log.info('Successfully Initialized: {} - Serial no: {}'.format(rs_name, rs_serial))

        log.info('\n##############################')
        log.info('Initializing Intel Neural Compute Stick.')
        # get the model ( Neural Compute Stick .xml) expected path:
        model = os.path.join(ML_MODEL_BASE_PATH, ML_MODEL_NAME) +'.xml'
        # get the model weights ( Neural Compute Stick .bin) expected path:
        weights = os.path.join(ML_MODEL_BASE_PATH, ML_MODEL_NAME) +'.bin'
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
                log.info('Getting colour and depth frame from RealSense as NP array')
                rs_frames = rs.get_rbg_depth_frames()

                # Convert to Np array and depth color map. 
                rs_frames_np = rs.get_frames_as_np_array(rs_frames)
                rbg = rs_frames_np['color_frame_np']
                depth_colormap = rs_frames_np['depth_frame_np']

                log.info('Performing Inference.........')
                boxes = ncs.perform_inference(rbg, confidence_threshold) 
                
                if(len(boxes) <= 0):
                    log.info("No Objected Detected / Found")
                else:
                    log.info("Found / Detected: {} objects".format(len(boxes)))
                    box = boxes[0][0]
                    center_pt = get_box_center(box)
                    log.info('Calculating depth to first object at: {}'.format(center_pt))

                    zDepth = rs.get_distance_to_frame_pixel(rs_frames['depth_frame'], center_pt['x'], center_pt['y'])
                    log.info('Detected an object at: {} meters\n'.format(zDepth))

                    # Uncomment below to save the latest processed (box-bound) image and depth colour map locally if desired
                    # Note: Be careful if saving unique image names with a high loop count as will quickly fill up a Pi disk
                    save_box_bound_Image(rbg, "image.bmp", boxes[0], "Person: {} meters".format(zDepth))
                    save_box_bound_Image(depth_colormap, "colormap.bmp", boxes[0], "Person: {} meters".format(zDepth))

                    # Inc image processed count
                    image_cnt += 1

                    # Add a sleep delay between taking next frames.
                    time.sleep(sleep_iteration)

            except KeyboardInterrupt:
                total_time = time.time() - start
                log.info("Completed {} image inference in {} seconds at {} Inference FPS".format(image_cnt, total_time, image_cnt / total_time))
                sys.exit()

    except Exception as e:
        log.info(e)
        log.info(traceback.format_exc())
    
    finally:
        print('Closing RealSense Connection......')
        rs.close_realsense_connection()
    

def save_box_bound_Image(image, saveas, boxes, annotation=None):

    saveas_path = os.path.join(IMAGE_SAVE_DIR, saveas)

    for box in boxes:
        cv2.rectangle(image, (box[0], box[1]), (box[2], box[3]), (0, 0, 255), 2)

    if annotation:
        font = cv2.FONT_HERSHEY_SIMPLEX
        org = (box[0], box[1] - 5)
        fontScale = 0.75
        color = (0, 0, 255)
        thickness = 1
        image = cv2.putText(image, annotation, org, font, fontScale, color, thickness, cv2.LINE_AA) 
        
    cv2.imwrite(saveas_path, image)

def get_box_center(box):
    xmin, ymin, xmax, ymax = box
    x_center = int(xmin + ((xmax - xmin) / 2))
    y_center = int(ymin + ((ymax - ymin) / 2))
    return {'x': x_center, 'y': y_center}

if __name__ == "__main__":

    workflow_realsense_simple()
