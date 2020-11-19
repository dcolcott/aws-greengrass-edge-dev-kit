# realsense-simple.py
#
# TBA  
#
# Author: Dean Colcott - https://www.linkedin.com/in/deancolcott/
#
# Cerdit: Intel OpenVino pPthon examples
#

from __future__ import print_function
import sys
import os
import cv2
import numpy as np
import logging
from openvino.inference_engine import IECore
from argparse import ArgumentParser, SUPPRESS

DEVICE = "MYRIAD"   # Specify making inference on NCS MYRIAD processor

# TEST_IMAGE_FILE = "../../sample-pics/faces01.jpeg"
# IMAGE_FILE = "../../sample-pics/girl_pearl_earings.png"

# Config the logger.
log = logging.getLogger(__name__)
logging.basicConfig(format="%(asctime)s - %(name)s - [%(levelname)s] - %(message)s", stream=sys.stdout, level=logging.INFO)

class IntelNcs():
    """
    Interact with the Intel Neural Compute Stick2 to perform single image inference
    """

    def __init__(self, model, weights):

        # --------------------------- 1. Read IR Generated by ModelOptimizer (.xml and .bin files) ------------
        log.info("Loading Intel Compute Stick Inference Engine with model: {}".format(model))
        ie = IECore()

        assert os.path.exists(model), "The model file: {} wasn't found".format(model)
        assert os.path.exists(weights), "The model weights file: {} wasn't found".format(weights)

        log.info("Loading network files:\n\t{}\n\t{}".format(model, weights))
        net = ie.read_network(model=model, weights=weights)

        # -----------------------------------------------------------------------------------------------------

        # ------------- 2. Load Plugin for inference engine and extensions library if specified --------------
        log.info("Device Inference Engine info:")
        versions = ie.get_versions(DEVICE)
        log.info("{}{}".format("." * 8, DEVICE))
        log.info("{}MKLDNNPlugin version ......... {}.{}".format("." * 8, versions[DEVICE].major, versions[DEVICE].minor))
        log.info("{}Build ........... {}".format("." * 8, versions[DEVICE].build_number))
        # -----------------------------------------------------------------------------------------------------

        # --------------------------- 3. Read and preprocess model input --------------------------------------------
        for input_key in net.input_info:
            log.info("input shape: " + str(net.input_info[input_key].input_data.shape))
            log.info("input key: " + input_key)
            layout_len = len(net.input_info[input_key].input_data.layout)
            if layout_len == 4:
                self.n, self.c, self.h, self.w = net.input_info[input_key].input_data.shape
                assert self.n == 1, 'Only supports models with shape number images (n) = 1 but loaded model requires: {}'.format(self.n)
            else:
                raise Exception('Only supports model input_data.layout = 4 (e.g: [1, 3, 512, 512]) but loaded model has data.shape: {}'.format(net.input_info[input_key].input_data.layout))
        # -----------------------------------------------------------------------------------------------------

        # --------------------------- 4. Configure input & output ---------------------------------------------
        # --------------------------- Prepare input blobs -----------------------------------------------------

        log.info("Preparing input blobs")
        assert (len(net.input_info.keys()) == 1 or len(net.input_info.keys()) == 2), "Sample supports topologies only with 1 or 2 inputs"
        self.out_blob = next(iter(net.outputs))
        self.input_name, self.input_info_name = "", ""

        for input_key in net.input_info:
            input_data_layout = net.input_info[input_key].layout
            log.info("Input data layout: {}".format(input_data_layout))
            if len(input_data_layout) == 4:
                self.input_name = input_key
                batch_size = net.batch_size
                log.info("Batch size is {}".format(net.batch_size))
                if net.batch_size != 1:
                    raise Exception('Only supports a batch size of 1 but found: {}'.format(net.batch_size))
                net.input_info[input_key].precision = 'U8'
            elif len(net.input_info[input_key].layout) == 2:
                self.input_info_name = input_key
                net.input_info[input_key].precision = 'FP32'
                if net.input_info[input_key].input_data.shape[1] != 3 and net.input_info[input_key].input_data.shape[1] != 6 or \
                    net.input_info[input_key].input_data.shape[0] != 1:
                    log.error('Invalid input info. Should be 3 or 6 values length.')


        # --------------------------- Prepare output blobs ----------------------------------------------------
        log.info('Preparing output blobs')

        output_name, output_info = "", net.outputs[next(iter(net.outputs.keys()))]
        for output_key in net.outputs:
            if net.layers[output_key].type == "DetectionOutput":
                output_name, output_info = output_key, net.outputs[output_key]

        if output_name == "":
            log.error("Can't find a DetectionOutput layer in the topology")

        output_dims = output_info.shape
        if len(output_dims) != 4:
            log.error("Incorrect output dimensions for SSD model")
        max_proposal_count, object_size = output_dims[2], output_dims[3]

        if object_size != 7:
            log.error("Output item should have 7 as a last dimension")

        output_info.precision = "FP32"

        # --------------------------- 5. Load Model to Device ---------------------------------------------
        log.info("Loading model to the device")
        self.exec_net = ie.load_network(network=net, device_name=DEVICE)


    def perform_inference(self, rbg, confidence_threashold):
        # --------------------------- 6. Perform Inference ---------------------------------------------
        
        # Get the inference image details
        images_hw = []
        ih, iw = rbg.shape[:-1]
        images_hw.append((ih, iw))

        # log.debug("File was added: {}".format(IMAGE_FILE))
        if (ih, iw) != (self.h, self.w):
            log.debug("Image is resized from {} to {}".format(rbg.shape[:-1], (self.h, self.w)))
            tmp_image = cv2.resize(rbg, (self.w, self.h))
        
        image = tmp_image.transpose((2, 0, 1))  # Change data layout from HWC to CHW

        data = {}
        data[self.input_name] = image

        if self.input_info_name != "":
            infos = np.ndarray(shape=(self.n, self.c), dtype=float)
            for i in range(n):
                infos[i, 0] = self.h
                infos[i, 1] = self.w
                infos[i, 2] = 1.0
            data[self.input_info_name] = infos

        # --------------------------- Performing inference ----------------------------------------------------

        log.debug("Creating infer request and starting inference")
        res = self.exec_net.infer(inputs=data)

        # --------------------------- Read and postprocess output ---------------------------------------------
        log.debug("Processing output blobs")
        res = res[self.out_blob]
        boxes, classes = {}, {}
        data = res[0][0]

        for number, proposal in enumerate(data):
            if proposal[2] > confidence_threashold:
                imid = np.int(proposal[0])
                ih, iw = images_hw[imid]
                label = np.int(proposal[1])
                confidence = proposal[2]
                xmin = np.int(iw * proposal[3])
                ymin = np.int(ih * proposal[4])
                xmax = np.int(iw * proposal[5])
                ymax = np.int(ih * proposal[6])
                log.debug("[{},{}] element, prob = {:.6}    ({},{})-({},{}) batch id : {}" \
                    .format(number, label, confidence, xmin, ymin, xmax, ymax, imid), end="")

                if not imid in boxes.keys():
                    boxes[imid] = []
                boxes[imid].append([xmin, ymin, xmax, ymax])
                if not imid in classes.keys():
                    classes[imid] = []

                classes[imid].append(label)

        return(boxes)
