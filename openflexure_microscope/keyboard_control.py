# -*- coding: utf-8 -*-
#!/usr/bin/env python
"""
Simple keyboard-based controller for the OpenFlexure Microscope.

Written 2016 by Richard Bowman, Abhishek Ambekar, James Sharkey and Darryl Foo
Substantially rewritten 2018 by Richard Bowman

Released under GNU GPL v3 or later.

Usage:
    python -m openflexure_microscope

Options:
      --output=<filepath>   Set output directory/filename [default: ~/Desktop/images]
      -h --help             Show this screen.
"""

import io
import sys
import os
import time
import argparse
import numpy as np
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

def parse_command_line_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Control the microscope using keyboard commands")
    parser.add_argument("--output", help="directory or filepath (with %d wildcard) for saved images", default="~/Desktop/images")
    args = parser.parse_args()
    return args

def adjust_attribute(obj, attrname, action, linear_increment=None, log_factor=None, minv=None, maxv=None):
    """Increment, decrement, or change the value of a property.
    
    Arguments:
        
    obj: the object on which the property is to be adjusted
    attrname: a string naming the property to be adjusted
    action: a positive or negative number if the property is to be 
        increased or decreased.  None for no change, and "?" to
        prompt the user to enter a value.
    linear_increment: a number that is added/subtracted
    log_factor: a number by which the property is multiplied/divided
    minv: a value below which the property can't be decreased
    maxv: a value above which the property can't be increased
    """
    pass #pval = getattr(obj, attrname)



def control_microscope_with_keyboard(output="./images"):
    filepath = validate_filepath(output)

    with load_microscope("microscope_settings.npz") as ms:
        camera = ms.camera
        stage = ms.stage
        camera.annotate_text_size=50
        print("wasd to move in X/Y, qe for Z\n"
              "r/f to decrease/increase step size.\n"
              "v/b to start/stop video preview.\n"
              "i/o to zoom in/out.\n"
              "[/] to select camera parameters, and +/- to adjust them\n"
              "j to save jpeg file, k to change output path.\n"
              "x to quit")
        step = 100
        fov = 1
        adjustable_parameters = [
                None,
                "step_size",
                "shutter_speed",
                "analog_gain",
                "digital_gain",
                "contrast", 
                "brightness", 
                "awb_gains",
                "position",
                ]
        current_parameter = 0
            
        while True:
            c = readkey()
            if c == 'x': #quit
                break
            elif c in ['w', 'a', 's', 'd', 'q', 'e']:
                # move the stage with quake-style keys
                move = {'w': [0,step,0],
                        'a': [step,0,0],
                        's': [0,-step,0],
                        'd': [-step,0,0],
                        'q': [0,0,-step],
                        'e': [0,0,step]}[c]
                stage.move_rel(move)
            elif c == "r":
                step /= 2
            elif c == "f":
                step *= 2
            elif c == 'i':
                fov *= 0.75
                camera.zoom = (0.5-fov/2, 0.5-fov/2, fov, fov)
            elif c == 'o':
                if fov < 1.0:
                    fov *= 4.0/3.0
                camera.zoom = (0.5-fov/2, 0.5-fov/2, fov, fov)
            elif c in ['[', ']', '-', '_', '=', '+']:
                if c in ['[', ']']: # scroll through parameters
                    N = len(adjustable_parameters)
                    d = 1 if c == ']' else -1
                    current_parameter = (current_parameter + N + d) % N
                    change = 0
                elif c in ['+', '=']: # change the current parameter
                    change = 1
                else:
                    change = -1
                pname = adjustable_parameters[current_parameter]
                if pname == "step_size":
                    if change != 0:
                        step = step * 2 if change > 0 else step // 2
                    pval = step
                elif pname == "shutter_speed":
                    if change > 0 and camera.shutter_speed <= 1000000:
                        camera.shutter_speed = int(camera.shutter_speed * 2**0.25)
                    elif change < 0 and camera.shutter_speed >= 1000:
                        camera.shutter_speed = int(camera.shutter_speed * 0.5**0.25)
                    pval = camera.shutter_speed
                elif pname == "analog_gain":
                    if change > 0 and camera.analog_gain <= 4:
                        camera.analog_gain = (camera.analog_gain * 2**0.25)
                    elif change < 0 and camera.analog_gain >= 0.1:
                        camera.analog_gain = (camera.analog_gain * 0.5**0.25)
                    pval = camera.analog_gain
                elif pname == "digital_gain":
                    if change > 0 and camera.digital_gain < 4:
                        camera.digital_gain *= 1.25
                    elif change < 0 and camera.digital_gain > 1:
                        camera.digital_gain /= 1.25
                    pval = camera.digital_gain
                elif pname == "brightness":
                    if change > 0 and camera.brightness <= 90:
                        camera.brightness += 10
                    if change < 0 and camera.brightness >= 10:
                        camera.brightness -= 10
                    pval = camera.brightness
                elif pname == "contrast":
                    if change > 0 and camera.contrast <= 90:
                        camera.contrast += 10
                    if change < 0 and camera.contrast >= 10:
                        camera.contrast -= 10
                    pval = camera.contrast
                elif pname == "awb_gains":
                    pval = (float(camera.awb_gains[0]),float(camera.awb_gains[1]))
                elif pname == "position":
                    pval = str(stage.position)
                message = "{}: {}".format(pname, pval)
                if pname is not None:
                    print(message)
                    camera.annotate_text = message
                else:
                    camera.annotate_text = ""
            elif c == "v":
                #camera.start_preview(resolution=(1080*4//3,1080))
                camera.start_preview(resolution=(489*4//3,480))
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
            elif c == "k":
                camera.stop_preview()
                new_filepath = raw_input("The new output location can be a directory or \n"
                                         "a filepath.  Directories will be created if they \n"
                                         "don't exist, filenames must contain '%d' and '.jp'.\n"
                                         "New filepath: ")
                if len(new_filepath) > 3:
                    filepath = validate_filepath(new_filepath)
                print("New output filepath: %s\n" % filepath)

    


if __name__ == '__main__':
    args = parse_command_line_arguments()
    control_microscope_with_keyboard(**args)

