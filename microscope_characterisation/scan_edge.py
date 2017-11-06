"""
A script to take a series of images of an edge, either side of
focus, to evaluate the resolution of the microscope.

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
    except IndexError:
        output_dir = "--help"
    if "--help" in output_dir:
        print "Usage: scan_edge.py <output_dir> <x shift> <y shift>"
        print "If x and y shift are specified, we do the scan 3 times"
        print "once at the present position, once at -shift, once at +shift."
        exit(0)
    os.makedirs(output_dir)

    try:
        xy_shift = np.array([sys.argv[2], sys.argv[3], 0], dtype=np.int)
    except IndexError:
        xy_shift = None

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
#        ms.autofocus(log_dz_array(40, 1.5, 11))
        #camera.zoom=(0.0,0.0,1.0,1.0)
        time.sleep(1)
        pos = np.array(stage.position)
        if xy_shift is not None:
            starting_positions = [pos - xy_shift, pos, pos + xy_shift]
            foldernames = ["neg_%d_%d" % tuple(xy_shift[:2]), "centre", "pos_%d_%d" % tuple(xy_shift[:2])]
        else:
            starting_positions = [pos]
            foldernames = ["centre"]

        for startpos, fname in zip(starting_positions, foldernames):
            os.makedirs(os.path.join(output_dir, fname))
            if np.any(startpos != stage.position):
                stage.move_abs(startpos)

#            ms.autofocus(dz_array(100,10), backlash=backlash)
                    
            for i in ms.scan_z(log_dz_array(30,1.2, 15)):
                time.sleep(3)
                camera.capture(os.path.join(output_dir,fname,"edge_zstack_raw_%03d_x%d_y%d_z%d.jpg" % ((i,) + tuple(stage.position))), use_video_port=False, bayer=True)
                camera.capture(os.path.join(output_dir,fname,"edge_zstack_%03d_x%d_y%d_z%d.jpg" % ((i,) + tuple(stage.position))), use_video_port=False)
        time.sleep(0.5)
        stage.move_rel(np.array(pos) - np.array(stage.position))

        
    #plt.show()
 
    print "Done :)"

