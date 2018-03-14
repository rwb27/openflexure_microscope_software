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

class InteractiveParameter(object):
    """This class is intended to allow a setting to be easily controlled.

    The basic version allows the value to be picked from a list.
    """
    _value = None
    name = ""
    allowed_values = []
    wrap = False

    def __init__(self, name, allowed_values, wrap=False, initial_value=None, readonly=False):
        """Create an object to manage a parameter.

        name: the name of the setting
        allowed_values: a list of values which are permitted
        wrap: whether incrementing past the end wraps to the start.
        """
        self.name = name
        self.allowed_values = allowed_values
        self.wrap = wrap
        self.readonly = readonly
        if initial_value is None:
            self._value = allowed_values[0]
        else:
            self._value = initial_value

    @property
    def value(self):
        """The value of the property we're manipulating"""
        return self._value
    @value.setter
    def value(self, newvalue):
        if not self.readonly:
            self._value = newvalue
        else:
            print("Warning: {} is a read-only property.".format(self.name))

    def current_index(self):
        """The index (in the allowed_values list) of the current value."""
        try:
            return list(self.allowed_values).index(self.value)
        except ValueError:
            try:
                allowed = np.array(self.allowed_values)
                return np.argmin((allowed - float(self.value))**2)
            except:
                print("Warning: the value of {} was {}, which is neither "
                      "allowed nor numerical!".format(self.name, self.value))
                return 0

    def change(self, step):
        """Change the value of this property by +/- 1 step"""
        assert step in [-1, 1], "Step must be in [-1, 1]"
        if self.readonly:
            return #don't change the property if we can't change it!
        i = self.current_index() + step
        N = len(self.allowed_values)
        if self.wrap:
            i = (i + N) % N # this ensures we wrap if i would be invalid
        if i >= 0 and i < N:
            self.value = self.allowed_values[i]

class InteractiveCameraParameter(InteractiveParameter):
    """An InteractiveParameter to control a camera property."""
    def __init__(self, camera, name, allowed_values, getter_conversion=lambda x: x, setter_conversion=lambda x: x, **kwargs):
        """See InteractiveParameter for details - first arg is a PiCamera."""
        self._camera = camera
        self.getter_conversion = getter_conversion
        self.setter_conversion = setter_conversion
        InteractiveParameter.__init__(self, name, allowed_values, **kwargs)

    @property
    def value(self):
        return self.getter_conversion(getattr(self._camera, self.name))
    @value.setter
    def value(self, newvalue):
        if not self.readonly:
            print("setting {} to {} (converted from {}).".format(self.name, newvalue, self.setter_conversion(newvalue)))
            setattr(self._camera, self.name, self.setter_conversion(newvalue))
        else:
            print("Warning: {} is a read-only property.".format(self.name))

class ReadOnlyObjectParameter(InteractiveParameter):
    """A dummy InteractiveParameter that only reads things."""
    def __init__(self, obj, name, filter_function=lambda x: x):
        """Create a dummy parameter that reads a value from an object."""
        self.obj = obj
        self.filter_function = filter_function
        InteractiveParameter.__init__(self, name, [None], readonly=True)

    @property
    def value(self):
        return self.filter_function(getattr(self.obj, self.name))

    def current_index(self):
        return 0

    def change(self, d):
        pass


def control_parameters_from_microscope(microscope):
    """Create a list of InteractiveParameter objects to control a microscope."""
    cam = microscope.camera
    stage = microscope.stage
    return [
            InteractiveParameter(None, [None]), # TODO: find a nicer way to hide the parameter display!
            InteractiveParameter("step_size", 2**np.arange(14), initial_value=256),
            InteractiveCameraParameter(cam, "shutter_speed", 10.0**np.linspace(2,5,28), setter_conversion=int),
            InteractiveCameraParameter(cam, "analog_gain", 2**np.linspace(-2,2,9)),
            InteractiveCameraParameter(cam, "digital_gain", 2**np.linspace(-2,2,9)),
            InteractiveCameraParameter(cam, "brightness", np.linspace(0,100,11), setter_conversion=int),
            InteractiveCameraParameter(cam, "contrast", np.linspace(-50,50,11), setter_conversion=int),
            ReadOnlyObjectParameter(cam, "awb_gains", filter_function=lambda (a, b): [float(a), float(b)]),
            ReadOnlyObjectParameter(stage, "position", filter_function=str),
            ]



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
        fov = 1 # TODO: turn this into a proper camera parameter
        control_parameters = control_parameters_from_microscope(ms)
        current_parameter = 0
        step_param = control_parameters[1] #TODO: select this based on name
        move_keys = {'w': [0,1,0],
                     'a': [1,0,0],
                     's': [0,-1,0],
                     'd': [-1,0,0],
                     'q': [0,0,-1],
                     'e': [0,0,1]}
        while True:
            c = readkey()
            if c == 'x': #quit
                break
            elif c in move_keys.keys():
                # move the stage with quake-style keys
                stage.move_rel( np.array(move_keys[c]) * step_param.value)
            elif c == "r":
                step_param.change(1)
            elif c == "f":
                step_param.change(-1)
            elif c == 'i':
                fov *= 0.75
                camera.zoom = (0.5-fov/2, 0.5-fov/2, fov, fov)
            elif c == 'o':
                if fov < 1.0:
                    fov *= 4.0/3.0
                camera.zoom = (0.5-fov/2, 0.5-fov/2, fov, fov)
            elif c in ['[', ']', '-', '_', '=', '+']:
                if c in ['[', ']']: # scroll through parameters
                    N = len(control_parameters)
                    d = 1 if c == ']' else -1
                    current_parameter = (current_parameter + N + d) % N
                    parameter = control_parameters[current_parameter]
                elif c in ['+', '=']: # change the current parameter
                    parameter.change(1)
                else: #c in ['-', ['_']:
                    parameter.change(-1)
                message = "{}: {}".format(parameter.name, parameter.value)
                if parameter.name is not None:
                    print(message)
                    camera.annotate_text = message
                else:
                    camera.annotate_text = ""
            elif c == "v":
                #camera.start_preview(resolution=(1080*4//3,1080))
                camera.start_preview(resolution=(480*4//3,480))
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

