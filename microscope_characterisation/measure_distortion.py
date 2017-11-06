"""
A script to take a series of images of an edge, scanned across the FoV,
in order to measure distortion of the field.

(c) Richard Bowman 2017, released under GPL v3
"""
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


def dz_array(step, n):
    """A list of Z displacements with a given number and spacing"""
    return (np.arange(n) - (n-1)/2.0) * step

def log_dz_array(min_step, log_factor, n):
    """A list of Z displacements with a given number and spacing"""
    half_steps = min_step * log_factor**(np.arange(np.floor(n/2)))
    half_dz = np.cumsum(half_steps)
    if n % 2 == 1:
        return np.concatenate([-half_dz[::-1], [0], half_dz])
    else:
        half_dz[0] /= 2
        return np.concatenate([-half_dz[::-1], half_dz])


if __name__ == "__main__":
    try:
        output_dir = sys.argv[1]
        xy_shift = np.array([sys.argv[2], sys.argv[3], 0], dtype=np.int)
        n_shifts = int(sys.argv[4])
    except IndexError:
        output_dir = "--help"

    if "--help" in output_dir:
        print "Usage: scan_edge.py <output_dir> <x shift> <y shift>"
        print "If x and y shift are specified, we do the scan 3 times"
        print "once at the present position, once at -shift, once at +shift."
        exit(0)
    os.makedirs(output_dir)

    with picamera.PiCamera(resolution=microscope.picam2_full_res) as camera, \
         OpenFlexureStage("/dev/ttyUSB0") as stage:
        camera.start_preview()
        ms = microscope.Microscope(camera, stage)
        time.sleep(3)
        ms.freeze_camera_settings(iso=320)
        #camera.shutter_speed = camera.shutter_speed / 2

        time.sleep(1)
        #plt.imshow(ms.rgb_image())
        #ms.cam.stop_preview()
        #plt.show()
        #ms.cam.start_preview()

        stage.backlash=128

        #camera.zoom=(0.4,0.4,0.2,0.2)
        #ms.autofocus(log_dz_array(100, 1.5, 11), backlash=backlash)
        #camera.zoom=(0.0,0.0,1.0,1.0)
        time.sleep(1)
        pos = stage.position

        ii = np.arange(n_shifts) - (n_shifts - 1.0)/2.0 # an array centred on zero
        scan_points = ii[:, np.newaxis] * xy_shift[np.newaxis, :]

        for i in ms.scan_linear(scan_points):
            time.sleep(1)
            camera.capture(os.path.join(output_dir,"edge_zstack_%03d_x%d_y%d_z%d.jpg" % ((i,) + tuple(stage.position))), use_video_port=False)
        time.sleep(0.5)

        
    #plt.show()
 
    print "Done :)"

