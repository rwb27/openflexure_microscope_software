# -*- coding: utf-8 -*-
#!/usr/bin/env python
"""
Simple stage control for Fergus Riche's "fergboard" controller.

Written 2016 by Richard Bowman, Abhishek Ambekar, James Sharkey and Darryl Foo

Released under GNU GPL v3 or later.

Usage:
    microscope_control.py [options] control [<step_size>]

Options:
      --output=<filepath>   Set output directory/filename [default: ~/Desktop/images]
      -h --help             Show this screen.
"""

import io
import sys
import os
import time
import numpy as np
import docopt
import picamera
from readchar import readchar, readkey
from openflexure_stage import OpenFlexureStage
from microscope import load_microscope

def validate_filepath(filepath):
    """Check the filepath is valid, creating dirs if needed
    The final format is  ~/Desktop/images/image_%d.img  
    %d is formatted with number by (filepath %n)
    https://pyformat.info/"""

    filepath = os.path.expanduser(filepath)
    if "%d" not in filepath and ".jp" not in filepath:
        if not os.path.isdir(filepath):
            os.mkdir(filepath)
        return os.path.join(filepath, "image_%03d.jpg")

    elif "%d" not in filepath and ".jp" in filepath:
        'add automatic numbering to filename'
        filepath = filepath.split('.')
        filepath = filepath[0] + '_%03d.' + filepath[1] 
        return filepath
    
    elif "%d" in filepath and ".jp" in filepath:
        return filepath
    
    else:
        raise ValueError("Error setting output filepath.  Valid filepaths should"
                         " either be [creatable] directories, or end with a "
                         "filename that contains '%d' and ends in '.jpg' or '.jpeg'")




#run microscope_control.py directly
if __name__ == '__main__':
    with load_microscope("microscope_settings.npz") as ms:
        print(ms.settings_dict())
        camera = ms.camera
        stage = ms.stage
        print("wasd to move in X/Y, qe for Z\n"
              "r/f to decrease/increase step.\n"
              "v/b to start/stop video preview.\n"
              "i/o to zoom in/out.\n"
              "t/g to adjust contrast, y/h to adjust brightness.\n"
              "j to save jpeg file, k to change output path.\n"
              "p to print current position, o to print AWB gains\n"
              "x to quit")
        step = 100 #int(argv.get('<step>',100))
        filepath = validate_filepath("~/Desktop/images/")#argv['--output'])
        fov = 1
        while True:
            c = readkey()
            if c == 'x': #quit
                break
            elif c == 'w':
                stage.move_rel([0,step,0])
            elif c == 'a':
                stage.move_rel([step,0,0])
            elif c == 's':
                stage.move_rel([0,-step,0])
            elif c == 'd':
                stage.move_rel([-step,0,0])
            elif c == 'q':
                stage.move_rel([0,0,-step])
            elif c == 'e':
                stage.move_rel([0,0,step])
            elif c == "r" or c == '-' or c == '_':
                step /= 2
            elif c == "f" or c == '+' or c == '=':
                step *= 2
            elif c == 'i':
                fov *= 0.75
                camera.zoom = (0.5-fov/2, 0.5-fov/2, fov, fov)
            elif c == 'o':
                if fov < 1.0:
                    fov *= 4.0/3.0
                camera.zoom = (0.5-fov/2, 0.5-fov/2, fov, fov)
            elif c == 't':
                if camera.contrast <= 90:
                    camera.contrast += 10
            elif c == 'g':
                if camera.contrast >= -90:
                    camera.contrast -= 10
            elif c == 'y':
                if camera.brightness <= 90:
                    camera.brightness += 10
            elif c == 'h':
                if camera.brightness >= -90:
                    camera.brightness -= 10
            elif c == 'n':
                if camera.shutter_speed <= 1000000:
                    camera.shutter_speed += 1000
            elif c == 'm':
                if camera.shutter_speed >= 1000:
                    camera.shutter_speed -= 1000
            elif c == "v":
                camera.start_preview(resolution=(3280/2,2464/2))
            elif c == "b":
                camera.stop_preview()
            elif c == "j":
                n = 0
                while os.path.isfile(os.path.join(filepath % n)):
                    n += 1
                camera.capture(filepath % n, format="jpg", bayer=True)
                camera.annotate_text="Saved '%s'" % (filepath % n)
                time.sleep(0.5)
                camera.annotate_text=""
            elif c == "p":
                print("Position: {}".format(stage.position))
                camera.annotate_text="Position '%s'" % str(stage.position)
                time.sleep(0.5)
                camera.annotate_text=""
            elif c == "o":
                camera.annotate_text="White balance {}".format(camera.awb_gains)
                time.sleep(0.5)
                camera.annotate_text=""
            elif c == "k":
                camera.stop_preview()
                new_filepath = raw_input("The new output location can be a directory or \n"
                                         "a filepath.  Directories will be created if they \n"
                                         "don't exist, filenames must contain '%d' and '.jp'.\n"
                                         "New filepath: ")
                if len(new_filepath) > 3:
                    filepath = validate_filepath(new_filepath)
                print("New output filepath: %s\n" % filepath)

    


