# AWS Greengrass Edge Development Kit

#### Intel RealSense Standalone (locally executable, not AWS Lambda) Code Examples

Code examples in this directory can run as standalone Python3 scripts.

To execute:
* **Simpe Example:** ```python3 realsense-simple.py```
* **Advanced Example:** ```python3 realsense-advanced.py```

**Example:** The expected output is as below:
```
python3 realsense-advanced.py 
[ INFO ] Initialising Realsense Camera
[ INFO ] Intel RealSense D435I - Serial:021222123456 Successfully Initialised
[ INFO ] Captured realsense image - waiting for auto-exposure to adjust
[ INFO ] Captured wait frame: 0
[ INFO ] Captured wait frame: 1
[ INFO ] Captured wait frame: 2
[ INFO ] Captured wait frame: 3
[ INFO ] Captured wait frame: 4
[ INFO ] Starting depth image processing, press Ctl-C to exit.
[ INFO ] Distance to image center at 320 x 240 is: 3.27 meters
[ INFO ] Distance to image center at 320 x 240 is: 3.04 meters
[ INFO ] Distance to image center at 320 x 240 is: 3.34 meters
[ INFO ] Distance to image center at 320 x 240 is: 3.21 meters
[ INFO ] Distance to image center at 320 x 240 is: 3.32 meters
[ INFO ] Distance to image center at 320 x 240 is: 3.28 meters
[ INFO ] Distance to image center at 320 x 240 is: 3.41 meters
[ INFO ] Distance to image center at 320 x 240 is: 2.98 meters
^C[ INFO ] Exiting.....
[ INFO ] Capture frames on Intel RealSense D435I - Serial 021222123456 complete
[ INFO ] Realsense pipeline successfully closed
```

## Saved RBG and Color Images
The RPG and colorised depth (and processed depth if using advanced) images will be saved to: /home/pi/Desktop/
Or where ever you have set the DEPTH_IMAGE_PATH, DEPTH_COLORMAP_PATH, PROCESSED_DEPTH_COLORMAP_PATH, etc in the code examples. 

You can copy them to your local machine via SCP (assumuming you have SSH acess to the Raspberry Pi or edge device).