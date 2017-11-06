# simple test jig for picamera

import picamera
import cv2
import numpy as np
import scipy
from scipy import ndimage
import os
import sys
import time
import matplotlib.pyplot as plt
from openflexure_stage import OpenFlexureStage
import microscope

if __name__ == "__main__":
    with picamera.PiCamera(sensor_mode=3, resolution=(3280,2464)) as camera:
    #with picamera.PiCamera() as camera:
        camera.start_preview()
        ms = microscope.Microscope(camera, None)
        time.sleep(3)
        ms.freeze_camera_settings(iso=100)
#        camera.shutter_speed = camera.shutter_speed / 4
        time.sleep(1)
        camera.capture("test_image0.jpg")
        time.sleep(0.5)
        camera.capture("test_image1.jpg")
        camera.capture("test_image2.jpg")
        time.sleep(0.5)

        
    #plt.show()
 
    print "Done :)"

