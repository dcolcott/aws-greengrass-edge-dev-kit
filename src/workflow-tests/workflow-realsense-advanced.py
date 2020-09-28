#
# A test method to run a workflow on the Raspberry Pi that:
# 1) Take a color and depth frame from the RealSense Device,
# 2) Performs an inference against an Intel face-detect model (could be any model) on the Intel Neural Compute Stick and
# 3) If an object is detected:
#   a) Performs post-processing on the depth frame and 
#   b) Takes a depth measurement to the center of the object bounding box on the processed frame using the RealSense Device depth functionality.
#
#  Note: Uses the RealSense Advanced class that applies one of a library of a pre-set configurations with various 
#  objectives to optimise density, accuracy, range and resolution and also offers post-processing of the depth frame before a depth calculation is made
#
# Calls the same classes and functions as the AWS Greengrass Lambda to interact with the 
# RealSense Device and the Intel Neural Compute stick so is a convenient way to develop  and try out new functions locally.
#
# Author: Dean Colcott - https://www.linkedin.com/in/deancolcott/
#


import sys
import time
import cv2
import logging
import traceback
from neural_compute.intel_ncs import IntelNcs as Ncs
from realsense.realsense_advanced import RealsenseDevice as RealSenseAdvanced

TEST_IMAGE_FILE = "../../sample-pics/faces01.jpeg"

# Config the logger.
log = logging.getLogger(__name__)
logging.basicConfig(format="%(asctime)s - %(name)s - [%(levelname)s] - %(message)s", stream=sys.stdout, level=logging.INFO)

def workflow_realsense_advanced():
    """
    Perform workflow to take a image for the RealSense device, peform a inference on the Compute Stick and 
    if an object detected, to log the depth to the first detected object. 
    """
    try:

        # Initilising Realsense camera.
        log.info('\n##############################')
        log.info('Initilising Realsense camera.')
        rs = RealSenseAdvanced()

        log.info('\n##############################')
        log.info('Initilising Intel Neural Compute Stick.')
        ncs = Ncs()
        
        loop_cnt = 5
        sleep_iteration = 2
        start = time.time()

        log.info('Starting image inference loop.')

        for i in range(loop_cnt):

            log.info('Getting color and depth frame from Realsense  as NP array')
            rs_frames = rs.get_rbg_depth_frames()

            # Convert to Np array and depth color map. 
            rs_frames_np = rs.get_frames_as_np_array(rs_frames)
            rbg = rs_frames_np['color_frame_np']
            depth_colormap = rs_frames_np['depth_frame_np']

            log.info('Peforming Inference.........')
            boxes = ncs.peform_inference(rbg)

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
                # Also Note: Saving to file will ~ half the frame rate the device is capable of. 

                save_box_bound_Image(rbg, "image.bmp", boxes[0], "Person: {} meters".format(zDepth))
                save_box_bound_Image(depth_colormap, "colormap.bmp", boxes[0], "Person: {} meters".format(zDepth))
                save_box_bound_Image(filtered_colormap, "filtered_colormap.bmp", boxes[0], "Person: {} meters".format(zDepth))

            # Uncomment below to add a sleep dely between taking frames if desired
            #print('Sleeping for: {} seconds\n\n'.format(sleep_iteration))
            #time.sleep(sleep_iteration)

        total_time = time.time() - start
        log.info("Completed {} inference in {} seconds at {} Inference FPS".format(loop_cnt, total_time, loop_cnt / total_time))

    except KeyboardInterrupt:
        log.info('Exiting.....')
        sys.exit()

    except Exception as e:
        log.info(e)
        log.info(traceback.format_exc())
    
    finally:
        rs.close_realsense_connection()
    

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


if __name__ == "__main__":

    workflow_realsense_advanced()
