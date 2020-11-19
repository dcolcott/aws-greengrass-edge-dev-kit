#
# A test method to run a workflow on the Raspberry Pi that will:
# 1) Take a color and depth frame from the RealSense Device,
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
# 1) Connect the realsense camera and Neural Compute Stick to the USB3 ports,
# 2) Load the desired Intel model into a directory:/home/pi/Documents/compute-stick-build/ (or update ML_MODEL_BASE_PATH below),
# 3) Uopdate the ML_MODEL_NAME 
# 3) CD into the src dorectory: cd src/
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
logging.basicConfig(format="%(asctime)s - %(name)s - [%(levelname)s] - %(message)s", stream=sys.stdout, level=logging.INFO)

# Inference Confidance threashold needed to register a detected object and post to MQTT
CONFIDENCE_THREASHOLD = 0.5

# Just for development, manually add the Intel model files (.bin and .xml) to Greengrass Core in /home/pi/compute-stick-build/
ML_MODEL_BASE_PATH = '/home/pi/Documents/compute-stick-build/'

# name of model to use for object detection.
ML_MODEL_NAME = 'face-detection-adas-0001'

# Parent directory to save processed image and distanbce color map
IMAGE_SAVE_DIR = '/home/pi/Desktop'

def workflow_realsense_advanced():
    """
    Perform workflow to take an image for the RealSense device, peform a inference on the Neural Compute Stick and 
    if an object detected, to log the depth to the first detected object. 
    """
    try:

        # Initilising Realsense camera.
        log.info('\n##############################')
        log.info('Initilising Realsense camera.')
        rs = RealSenseAdvanced()
        rs_name = rs.get_device_name()
        rs_serial = rs.get_device_serial()
        log.info('Successfully Initilised: {} - Serial no: {}'.format(rs_name, rs_serial))

        log.info('\n##############################')
        log.info('Initilising Intel Neural Compute Stick.')
        # get the model ( Neural Compute Stick .xml) expected path:
        model = os.path.join(ML_MODEL_BASE_PATH, ML_MODEL_NAME) +'.xml'
        # get the model weights ( Neural Compute Stick .bin) expected path:
        weights = os.path.join(ML_MODEL_BASE_PATH, ML_MODEL_NAME) +'.bin'
        # Initilise the Neural Compute Stick with the selected model.
        ncs = Ncs(model, weights)
        log.info('Successfully Initilised Neural Compute Stick')

        # Set the sleep time and loop iteration variables and start timer.
        sleep_iteration = 2
        image_cnt = 0
        start = time.time()

        confidence_threashold = CONFIDENCE_THREASHOLD

        log.info('Starting image inference loop.')
        
        while True:

            try:
                log.info('Getting color and depth frame from Realsense as NP array')
                rs_frames = rs.get_rbg_depth_frames()

                # Convert to Np array and depth color map. 
                rs_frames_np = rs.get_frames_as_np_array(rs_frames)
                rbg = rs_frames_np['color_frame_np']
                depth_colormap = rs_frames_np['depth_frame_np']

                log.info('Peforming Inference.........')
                boxes = ncs.peform_inference(rbg, confidence_threashold) 
                
                if(len(boxes) <= 0):
                    log.info("No Objected Detected / Found")
                else:
                    log.info("Found / Detected: {} objects".format(len(boxes)))
                    box = boxes[0][0]
                    center_pt = get_box_center(box)
                    log.info('Calculating depth to first object at: {}'.format(center_pt))

                    # Get Filtered / Post-Processed depth frame to improve quality / result
                    log.info('Applying filtering / post-processing to depth frame')
                    filtered_frame = rs.get_post_process_depth_frame(rs_frames['depth_frame'])
                    filtered_colormap = rs.get_frames_as_np_array({'filtered_frame' : filtered_frame})
                    filtered_colormap = filtered_colormap['filtered_frame_np']

                    # TODO: FIltered frame changes the image size, need to move above the inference 
                    # or get the size difference to calculate the bounding box.
                    # For now, just take depth from non-filtered depth frame
                    zDepth = rs.get_distance_to_frame_pixel(rs_frames['depth_frame'], center_pt['x'], center_pt['y'])
                    log.info('Detected an object at: {} meters\n'.format(zDepth))

                    # Uncomment below to save the latest processed (box-bound) image and depth color map locally if desired
                    # Note: Be careful if saving unique image names with a high loop count as will quickly fill up a Pi disk
                    save_box_bound_Image(rbg, "image.bmp", boxes[0], "Person: {} meters".format(zDepth))
                    save_box_bound_Image(depth_colormap, "colormap.bmp", boxes[0], "Person: {} meters".format(zDepth))
                    save_box_bound_Image(filtered_colormap, "filtered_colormap.bmp", boxes[0], "Person: {} meters".format(zDepth))

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
        print('Closing Realsense Connection......')
        rs.close_realsense_connection()
    

def save_box_bound_Image(image, saveas, boxes, annatation=None):

    saveas_path = os.path.join(IMAGE_SAVE_DIR, saveas)

    for box in boxes:
        cv2.rectangle(image, (box[0], box[1]), (box[2], box[3]), (0, 0, 255), 2)

    if annatation:
        font = cv2.FONT_HERSHEY_SIMPLEX
        org = (box[0], box[1] - 5)
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

if __name__ == "__main__":

    workflow_realsense_advanced()