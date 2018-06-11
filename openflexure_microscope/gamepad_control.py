import pygame

def control_microscope_with_joystick(ms):
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
