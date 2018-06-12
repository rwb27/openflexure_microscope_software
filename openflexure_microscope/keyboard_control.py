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

class FunctionParameter(InteractiveParameter):
    def __init__(self, name, function, args=[], kwargs={}):
        """Create a 'parameter' to run a function.

        name: the name of the function
        function: the callable to run
        args, kwargs: arguments for the above
        """
        self.name = name
        self.function = function
        self.f_args = args
        self.f_kwargs = kwargs

    @property
    def value(self):
        return "press +"
    @value.setter
    def value(self):
        print("Cannot set the value of a function parameter")

    def current_index(self):
        return 0

    def change(self, step):
        self.function(*self.f_args, **self.f_kwargs)


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
            try:
                setattr(self._camera, self.name, self.setter_conversion(newvalue))
                time.sleep(0.3) # We wait so that, when we read back the value, it has updated.
                # the 0.3s time constant was determined by trial and error...
            except:
                print("Error setting camera.{} to {}.  Perhaps your version of "
                      "picamera does not support it?".format(self.name, newvalue))
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

def image_stack(ms, raw=False):
    """Acquire a stack of images, prompting the operator for parameters"""
    ms.camera.stop_preview()
    try:
        output_dir = os.path.expanduser(raw_input("Output directory: "))
        os.mkdir(output_dir)
        step_size = [int(raw_input("{} step size: ".format(ax))) for ax in ['X', 'Y', 'Z']]
        n_steps = int(raw_input("Number of images: "))
        ms.camera.start_preview()
        ms.camera.annotate_text = ""
        ms.acquire_image_stack(step_size, n_steps, output_dir, raw=raw)
        ms.camera.annotate_text = "Acquired {} images to {}".format(n_steps, output_dir)
        time.sleep(1)
    except Exception as e:
        print "Error: {}".format(e)


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
            FunctionParameter("coarse autofocus", microscope.autofocus, [np.linspace(-1280,1280,11)]),
            FunctionParameter("medium autofocus", microscope.autofocus, [np.linspace(-320,320,11)]),
            FunctionParameter("fine autofocus", microscope.autofocus, [np.linspace(-80,80,11)]),
            FunctionParameter("image stack", image_stack, [microscope]),
            FunctionParameter("image stack [raw]", image_stack, [microscope], {'raw':True}),
            InteractiveCameraParameter(cam, "brightness", np.linspace(0,100,11), setter_conversion=int),
            InteractiveCameraParameter(cam, "contrast", np.linspace(-50,50,11), setter_conversion=int),
            InteractiveCameraParameter(microscope, "zoom", 2**np.linspace(0,4,9)),
            ReadOnlyObjectParameter(cam, "awb_gains", filter_function=lambda (a, b): [float(a), float(b)]),
            ReadOnlyObjectParameter(stage, "position", filter_function=str),
            ]

def parameter_with_name(name, parameter_list):
    """Retrieve a parameter with the given name from a list"""
    for p in parameter_list:
        if p.name == name:
            return p
    raise KeyError("No parameter with the requested name was found.")

def control_microscope_with_keyboard(output="./images", dummy_stage=False, settings_file="microscope_settings.npz"):
    filepath = validate_filepath(output)

    with load_microscope(settings_file, dummy_stage=dummy_stage) as ms:
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
        control_parameters = control_parameters_from_microscope(ms)
        current_parameter = 0
        parameter = control_parameters[current_parameter]
        step_param = parameter_with_name("step_size", control_parameters)
        zoom_param = parameter_with_name("zoom", control_parameters)
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
            elif c in ['r', 'f']:
                step_param.change(1 if c=='r' else -1)
            elif c in ['i', 'o']:
                zoom_param.change(1 if c=='i' else -1)
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
                camera.capture(filepath % n, format="jpeg", bayer=True)
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

