# AWS Greengrass Edge Development Kit

Universal AWS IoT Greengrass edge development kit with ML Object Detection and Depth Perception. Based on a Raspberry Pi4, provides edge inference of RBG and depth images as well as an array of sensors and actuators. Interfaces include a GPIO controlled 8-port 250v/10A Relay board, I2C temperature, moisture, etc sensors and 8 x native GPIO pins and servo and DC motor controllers all managed from the AWS IoT and data platform. 

The pièce de résistance however is an Intel RealSense d453i depth perception camera and the Intel Neural Compute Stick 2 providing 3D and depth image ML inference on the edge with hardware accelerated neural processing. These are optional components depending on your budget (the project supports a simple webcam as well) but they go a long way to showing the kind of advanced peripheries and use-cases you can serve on the edge with AWS Greengrass. 

**Note:** This project is very much under development. Not all code examples are completed. I will be updating regularly until complete.

### AWS Greengrass Development Kit V1
![AWS Greengrass Development Kit V1](pics/dev-kit-front-back.png)

#### AWS Greengrass Development Kit V1 - Lid Off
![AWS Greengrass Development Kit V1 - Lid Off](pics/dev-kit-lid-off.png)

#### AWS Greengrass Development Kit V1 - Internal Wiring and Temp Sensor
![AWS Greengrass Development Kit V1 - Internal Wiring and Temp Sensor](pics/dev-kit-wired-up.png)

### Getting Started
If you want to build some or all of this project go to the [Getting Started](getting-started) folder to see all the details you need to start building. 

### Who is this Project For?
This project is to enable and encourage those with an interest in developing and learning advanced edge compute and computer vision use-cases using AWS IoT and AWS Greengrass.

* **Students:** Would make an awesome university / college engineering project.
* **Teachers / Lectures:** A great learning aid for classroom prac's and workshops.
* **IoT Specialists:** Developing professional skills on AWS and advanced IoT Edge Compute.
* **IoT Technology Businesses:** Low cost PoC / quick start to value realisation.
* **Developers:** Step by step guide to building deployment pipelines and code examples for AWS Greengrass.
* **Data Scientists:** To develop and test ML computer vision models on edge devices.
* **Home Automation / Security:** Bringing an array of 240v/10A and logic I/O's and computer vision managed from AWS cloud.
* **Enthusiasts:** Looking for the next interesting project in the rapidly growing world of edge compute and IoT.

 ### AWS Greengrass Lambdas To:
* Capture RealSense RBG and Depth Image, preform inference on Compute Stick and report depth to AWS IoT Core for any detected objects,
* Capture USB WebCam image, preform inference on Compute Stick and report any detected object types and co-ordinates to AWS IoT Core 
* Perform Image Inference on Mxnet Model on Ras Pi CPU (So depending on budget you don't need the Compute Stick)
* Capture local temperature from an I2C interface and report to AWS IoT Core,
* Actuate GPIO Relay Board based on various inputs such as GPIO inputs and computer vision object detection results
* Generic GPIO I/O.

### ReanSense Depth-Colour Maps

One of the key use-cases is to take a standard RGB image and use for inference against a machine learning object detection model then if one of the desired objects is detected, to take a distance measurement to it such as shown in the below depth colour maps:  
![Realsense Colour maps](pics/realsense-colormaps.png)

That's me at my desk writing this guide! The ML model detected a person and then measured a distance of just under 1 meter away.

### AWS Greengrass Development Kit V1 - CAD Designs

3D printed enclosure and internal standoffs (3D print STL files) included:

![AWS Greengrass Development Kit V1 - CAD Front - Back](pics/dev-kit-cad-front-back.png)

![AWS Greengrass Development Kit V1 - CAD Lid Off](pics/dev-kit-cad-lid-off.png)

### Example Use Cases for Computer Vision / Depth on Edge Compute with I/O Actuators

* **Safety**: Forklift or manufacturing machinery detect person in ‘Red / Danger Zone’ and action alarm / alert or machine stop via local relay. Cloud notification for analytical / BI of near miss.
* **Retail:** Person waiting at counter time and notification, counter queue depth count, etc
* **Robotics:** Collision avoidance, Drive to Object.
* **Robot Arm:** Detect and capture object. (Depth camera is detachable, can be mounted on robot arm extension). 
* **General Development:** Enablement, training and education on AWS Greengrass edge device capability.
