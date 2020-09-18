# AWS Greengrass Edge Development Kit

Universal AWS IoT Greengrass edge development kit with ML Object Detection and Depth Perception. Based on a Ras[berry Pi4 and provides edge inference of image and depth perception as well as a arrary of sensors and actuators. Interfaces include a GPIO controlled 8-port 250v/10A elay board, I2C temperature, moisture, etc sensors and 8 x native GPIO pins all controlled and managed from the AWS IoT and data platform. 

Code examples include standalone and AWS Lambda python code for:
* Capture synchronised Realsense RBG and Depth Image,
* Peform Image Inference on MXMET ML Model native on Raspberry Pi (So you don't need the Compute Stick)
* Peform Image Inference on Intel Neural Compute Stick 2
* Capture local temperature from a I2C interface,
* Actuate GPIO Relay Board
* Generic GPIO I/O.

#### AWS Greengrass Development Kit V1
![pics/v1/dev-kit-front-back.png](pics/v1/dev-kit-front-back.png)

#### AWS Greengrass Development Kit V1 - Lid Off
![pics/v1/dev-kit-front-back.png](pics/v1/dev-kit-lid-off.png)

#### AWS Greengrass Development Kit V1 - Lid Off
![pics/v1/dev-kit-front-back.png](pics/v1/dev-kit-expanded.png)



3D printed enclosure (3D STL files included) containing:
*  A Raspberry Pi4
* GPIO Controlled 250v/10A Relay board
* Intel Neural Compute Stick,
* Mount for Intel d354i Realsense 3D camera (or any supported USB WebCam)




