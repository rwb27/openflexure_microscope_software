# -*- coding: utf-8 -*-
#!/usr/bin/env python
"""
Simple stage control for Fergus Riche's "fergboard" controller.

Written 2016 by Richard Bowman, Abhishek Ambekar, James Sharkey and Darryl Foo

Released under GNU GPL v3 or later.

Usage:
    microscope move <x> <y> [<z>]
    microscope focus <z>
    microscope [options] control [<step_size>]
    microscope [options]

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
import curses
import curses.ascii
import picamera
from openflexure_stage import OpenFlexureStage

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
    pass
    
    argv = docopt.docopt(__doc__, options_first=True)
    
    stage = OpenFlexureStage('/dev/ttyUSB0')

    if argv['move']:
        x, y, z = [int(argv.get(d, 0)) for d in ['<x>', '<y>', '<z>']]
        print ("moving", x, y, z)
        stage.move_rel([x, y, z])
    elif argv['focus']:
        stage.focus_rel(int(argv['<z>']))
    else: #if argv['control']:
        def move_stage_with_keyboard(stdscr):
            stdscr.addstr(0,0,"wasd to move in X/Y, qe for Z\n"
                          "r/f to decrease/increase step.\n"
                          "v/b to start/stop video preview.\n"
                          "i/o to zoom in/out.\n"
                          "t/g to adjust contrast, y/h to adjust brightness.\n"
                          "j to save jpeg file, k to change output path.\n"
                          "x to quit\n")
            step = int(argv.get('<step>',100))
            filepath = validate_filepath(argv['--output'])
            fov = 1
            with picamera.PiCamera(resolution=(3280/2,2464/2)) as camera:
                #time.sleep(3)
                #camera.start_preview()
                #time.sleep(3)
                #camera.stop_preview()
                while True:
                    c = stdscr.getch()
                    if curses.ascii.isascii(c):
                        c = chr(c)
                    if c == 'x':
                        break
                    elif c == 'w' or c == curses.KEY_UP:
                        stage.move_rel([0,step,0])
                    elif c == 'a' or c == curses.KEY_LEFT:
                        stage.move_rel([step,0,0])
                    elif c == 's' or c == curses.KEY_DOWN:
                        stage.move_rel([0,-step,0])
                    elif c == 'd' or c == curses.KEY_RIGHT:
                        stage.move_rel([-step,0,0])
                    elif c == 'q' or c == curses.KEY_PPAGE:
                        stage.move_rel([0,0,-step])
                    elif c == 'e' or c == curses.KEY_NPAGE:
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
                        camera.start_preview()
                    elif c == "b":
                        camera.stop_preview()
                    elif c == "j":
                        n = 0
                        while os.path.isfile(os.path.join(filepath % n)):
                            n += 1
                        camera.capture(filepath % n, format="png", use_video_port=True)
                        camera.annotate_text="Saved '%s'" % (filepath % n)
                        try:
                            stdscr.addstr("Saved '%s'\n" % (filepath % n))
                        except:
                            pass
                        time.sleep(0.5)
                        camera.annotate_text=""
                    elif c == "p":
                        camera.annotate_text="Position '%s'" % str(stage.position)
                        try:
                            stdscr.addstr("Position '%s'\n" % str(stage.position))
                        except:
                            pass
                        time.sleep(0.5)
                        camera.annotate_text=""
                    elif c == "k":
                        camera.stop_preview()
                        stdscr.addstr("The new output location can be a directory or \n"
                                      "a filepath.  Directories will be created if they \n"
                                      "don't exist, filenames must contain '%d' and '.jp'.\n"
                                      "New filepath: ")
                        curses.echo()
                        new_filepath = stdscr.getstr()
                        curses.noecho()
                        if len(new_filepath) > 3:
                            filepath = validate_filepath(new_filepath)
                        stdscr.addstr("New output filepath: %s\n" % filepath)

        curses.wrapper(move_stage_with_keyboard)

    


