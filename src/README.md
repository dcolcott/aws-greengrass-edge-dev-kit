# AWS Greengrass Edge Development Kit

### Code Samples
This section provides python3 code examples for both standalone and AWS IoT Greengrass deployed functions. 

**The code provides includes:**  
1) **greengrasssdk:** The AWS IoT Greengrass SDK that must be packaged with any AWS Greengrass lambda.  
1) **neural_compute/:**  
    a) **intel_ncs.py:** Class to initialise and perform image inference on the Intel Neural Compute Stick.  
1) **realsense/:**  
    a) **preset-configs:** Directory of RS400 advanced pre-set configurations for the RealSense camera.  
    b) **realsense_simple.py:** Class to interact with the RealSense d4xx camera using mostly default settings.  
    c) **realsense_advanced.py:** Class to interact with the RealSense d4xx camera, to apply advanced settings form the preset-config directory and to apply depth frame post-processing / filtering.  
1) **workflow-tests/:** Directory containing standalone python code to perform various workflows for local development:   
    a) **workflow-cv-depth-symple.py:** Computer Vision / Depth Measurement workflow using the Neural Compute stick to perform object-detection and the RealSense camera to report the distance to the detected object.  
    b) **workflow-cv-depth-advanced.py:** Computer Vision / Depth Measurement workflow using the Neural Compute stick to perform object-detection and the RealSense camera to report the distance to the detected object. Uses the preset advanced configurations for the RealSense camera and provides depth frame post-processing and filtering.  
1) **lambda_cv_depth.py:** AWS IoT Greengrass Lambda functionfor Intel realsense d4xx camera and Intel Compute stick HW accellerated object detection inferenceand depth perception.   
1) **lambda_temp_measure.py:** AWS IoT Greengrass Lambda function for reading in temperature form the edge device over a I2C interface to a LM75a temperature sensor. Can use to measure and log the ambient temperature or as an environmental warning for the edge device by measuring the temperature inside the dev kit enclosure (The pi4 can run hot sometimes!).  
1) **lambda_gpio_relay.py:** AWS IoT Greengrass Lambda function for remotely controlling the 8 port relay board via the Ras Pi GPIO pins.  

### Packaging and Deploying a Lambda

To package up an AWS Lambda for deployment you just need to ZIP the appropriate files into a single file. All AWS IoT Greengrass Lambda functions need the greengrasssdk and the lambda_function.py which acts as the main method that is initially called when the Lambda is invoked. 

As an example, the Computer Vision Depth measurement function needs the Lambda entry point (**lambda_cv_depth.py:** ) and the greengrasssdk. Because this function also calls the RealSense and Neural Compute Stick functions, we need to include these in the package as well. 

**From the SRC folder:**  
* To create the deployment package for the Computer Vision Depth measurement function use the below command:  
**zip -r lambda-cv-depth.zip greengrasssdk realsense neural_compute lambda_cv_depth.py**  

* To create the deployment package for the temperature measurement function use the below command:  
**zip -r lambda-temp-meas.zip greengrasssdk lambda_temp_measure.py**  

* To create the deployment package for the GPIO Relay board control function use the below command:  
**zip -r lambda-gpio-relay.zip greengrasssdk lambda_gpio_relay.py.py**

Or you can also create the Zip from your desktop using any of the standard compression tools available on Windows or Mac. 

Pre-packaged zip's for all of the listed functions are available in the: [pre-packages-lambdas](pre-packages-lambdas) directory

For a more detailed guide on creating an AWS Lambda and deploying an AWS Greengrass package see the below reference guides:  
[What is AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/welcome.html)  
[Create a Lambda Function (Console)](https://docs.aws.amazon.com/lambda/latest/dg/getting-started-create-function.html)  
[Create a Lambda Function (CLI)](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-awscli.html)  
[AWS Lambda](https://aws.amazon.com/lambda/)  
[Package A Python Lambda](https://docs.aws.amazon.com/lambda/latest/dg/python-package.html)  
