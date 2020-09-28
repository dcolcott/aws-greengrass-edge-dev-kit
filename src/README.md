# AWS Greengrass Edge Development Kit

### Code Samples
This section provides python3 code examples for both standalone and AWS IoT Greengrass deployed functions. The code provides is:
1) **greengrasssdk:** The AWS IoT Greengrass SDK that must be packages with any AWS Greengrass lambda.
1) **neural_compute:**  
    a) **intel_ncs.py:** Class to initialise and perform image inference on the Intel Neural Compute Stick
1) **realsense:**
    a) **preset-configs:** Directory of RS400 advanced pre-set configurations for the RealSense camera.
    b) **realsense_simple.py:** Class to interact with the RealSense d4xx camera using mostly default settings.
    c) **realsense_advanced.py:** Class to interact with the RealSense d4xx camera, to apply advanced settings form the preset-config directory and to apply depth frame post-processing / filtering.
1) **workflow-tests:** Directory containing standalone python code to peform various workflows for local development:
    a) **workflow-cv-depth-symple.py:** Computer Vision / Depth Measurement workflow using the Neural Compute stick to peform object-detection and the RealSense camera to report the distance to the detected object.
    a) **workflow-cv-depth-advanced.py:** Computer Vision / Depth Measurement workflow using the Neural Compute stick to peform object-detection and the RealSense camera to report the distance to the detected object. Uses the preset advanced configurations for the RealSense camera and provides depth frame post-processing and filtering.
1) **lambda_cv_depth.py:** AWS IoT Greengrass lambda main method for Intel realsense d4xx camera and INtel Compute stick HW accellerated object detection inference. 

### Packaging and Deploying a Lambda

To package up a Lambda for deployment you just need to ZIP the appropriate files into a single file. All AWS IoT Greengrass lambda functions need the greengrasssdk and the lambda_function.py which acts as the main method that is initially called when the Lambda is invoked. 

In the case of the Computer Vision Depth measurement function it needs the Lambda entry point (**lambda_cv_depth.py:** ) and the greengrasssdk. Because this function also calls the RealSense and Neural Compute Stick functions, we need to include these in the package as well. So, to create the deployment package for the Computer Vision Depth measurement function use the below command:

# zip -r cv-edge-lambda.zip greengrasssdk realsense neural_compute lambda_cv_depth.py

You can also create the Zip form your desktop using any of the standard compression tools available on Windows or Mac. 

This will ZIP up all the required files into a ZIP called **cv-edge-lambda.zip** that is deployable to a AWS Lambda function. 

For a more detailed guide on creating a AWS Lambda and deploying an AWS Greengrass package see the below reference guides:
[What is AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/welcome.html)
[Create a Lambda Function (Console)](https://docs.aws.amazon.com/lambda/latest/dg/getting-started-create-function.html)
[Create a Lambda Function (CLI)](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-awscli.html)
[AWS Lambda](https://aws.amazon.com/lambda/)
[Package A Python Lambda](https://docs.aws.amazon.com/lambda/latest/dg/python-package.html)

