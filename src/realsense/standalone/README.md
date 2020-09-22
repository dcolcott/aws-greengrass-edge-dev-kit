# AWS Greengrass Edge Development Kit

#### Intel RealSense Code Examples

Code examples in this directory can run as standalone Python3 scripts.

To execute:
* **Simpe Example:** ```python3 realsense-simple.py```
* **Advanced Example:** ```python3 realsense-advanced.py```

**Example:** The expected output is as below:
```
[ INFO ] Initialising Realsense Camera
[ INFO ] Intel RealSense D435I - Serial:012222077364 Successfully Initialised
[ INFO ] Captured realsense image - waiting for auto-exposure to adjust
[ INFO ] Captured wait frame: 0
[ INFO ] Captured wait frame: 1
[ INFO ] Captured wait frame: 2
[ INFO ] Captured wait frame: 3
[ INFO ] Captured wait frame: 4
[ INFO ] Starting depth image processing, press Ctl-C to exit.
[ INFO ] Distance to image center at 424 x 240 is: 0.00 meters
[ INFO ] Distance to image center at 424 x 240 is: 3.94 meters
[ INFO ] Distance to image center at 424 x 240 is: 2.98 meters
[ INFO ] Distance to image center at 424 x 240 is: 2.93 meters
[ INFO ] Distance to image center at 424 x 240 is: 3.57 meters
[ INFO ] Distance to image center at 424 x 240 is: 3.11 meters
[ INFO ] Distance to image center at 424 x 240 is: 3.46 meters
^C[ INFO ] Exiting.....
[ INFO ] Capture frames on Intel RealSense D435I - Serial 012222077364 complete
[ INFO ] Realsense pipeline successfully closed
```

